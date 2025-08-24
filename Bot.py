import os
import re
import json
import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from pyrogram.errors import FloodWait

# ───────────────────────── CONFIG ─────────────────────────
API_ID = int(os.getenv("API_ID", "22768311"))
API_HASH = os.getenv("API_HASH", "702d8884f48b42e865425391432b3794")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # set this in your VPS env
OWNER_ID = int(os.getenv("OWNER_ID", "6040503076"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1003058967184"))

FIXED_COMMENT = "@CrunchyRollChannel For More Animes In Hindi!"

# ───────────────────────── Storage ─────────────────────────
DATA_DIR = Path("./data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
STORE_PATH = DATA_DIR / "storage.json"
TMP_DIR = DATA_DIR / "tmp"
THUMBS_DIR = DATA_DIR / "thumbs"
for p in (TMP_DIR, THUMBS_DIR):
    p.mkdir(parents=True, exist_ok=True)

DEFAULT_STORE = {
    "admins": [],          # [int]
    "thumbs": {},          # user_id(str) -> path
    "metadata": {},        # user_id(str) -> {status, title, author, artist, audio, subtitle, video}
}

def load_store() -> Dict[str, Any]:
    if not STORE_PATH.exists():
        STORE_PATH.write_text(json.dumps(DEFAULT_STORE, indent=2))
    try:
        return json.loads(STORE_PATH.read_text())
    except Exception:
        return DEFAULT_STORE.copy()

STORE = load_store()
def save_store():
    STORE_PATH.write_text(json.dumps(STORE, indent=2))

# ───────────────────────── App ─────────────────────────
app = Client("PrivateAutoRename", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def is_owner(uid: int) -> bool:
    return uid == OWNER_ID

def is_admin(uid: int) -> bool:
    return uid == OWNER_ID or uid in STORE.get("admins", [])

# ───────────────────────── Metadata store ─────────────────────────
def get_user_meta(uid: int) -> Dict[str, Optional[str]]:
    d = STORE.setdefault("metadata", {}).setdefault(
        str(uid),
        {"status": "Off", "title": None, "author": None, "artist": None, "audio": None, "subtitle": None, "video": None},
    )
    return d

def set_user_meta(uid: int, key: str, value: Optional[str]):
    meta = get_user_meta(uid)
    meta[key] = value
    save_store()

def set_meta_status(uid: int, status: str):
    meta = get_user_meta(uid)
    meta["status"] = "On" if status == "On" else "Off"
    save_store()

# ───────────────────────── Thumbs ─────────────────────────
def get_user_thumb(uid: int) -> Optional[str]:
    return STORE.get("thumbs", {}).get(str(uid))

def set_user_thumb(uid: int, path: str):
    STORE.setdefault("thumbs", {})[str(uid)] = path
    save_store()

def del_user_thumb(uid: int):
    p = STORE.get("thumbs", {}).pop(str(uid), None)
    save_store()
    if p:
        Path(p).unlink(missing_ok=True)

# ───────────────────────── Parsing helpers ─────────────────────────
QUALITY_RE = re.compile(r"(?:(?<=\b)|_)(360p|480p|720p|1080p|1440p|2160p|2K|4K)(?=\b|_)", re.IGNORECASE)
EP_RE_LIST = [
    re.compile(r"\bE(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"\bEp(?:isode)?\s*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"[\[\(]\s*(\d{1,3})\s*[\]\)]"),  # [01], (01)
    re.compile(r"(?<!\d)(\d{1,3})(?!\d)")  # lone numbers
]
SEASON_LIKE_RE = re.compile(r"\bS(\d{1,2})\b", re.IGNORECASE)
LITERAL_SEASON_IN_FMT_RE = re.compile(r"S\d{2}")

def ensure_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def detect_quality_from_filename(name: str) -> Optional[str]:
    m = QUALITY_RE.search(name or "")
    return m.group(1) if m else None

def probe_height(path: str) -> Optional[int]:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=height", "-of", "csv=p=0", path],
            stderr=subprocess.STDOUT,
            text=True
        ).strip()
        return int(out) if out.isdigit() else None
    except Exception:
        return None

def quality_from_height(h: Optional[int]) -> Optional[str]:
    if not h: return None
    if h >= 1400: return "1440p" if h < 2000 else "2160p"
    if h >= 1000: return "1080p"
    if h >= 700:  return "720p"
    if h >= 500:  return "480p"
    if h >= 300:  return "360p"
    return None

def extract_episode(name: str) -> Optional[int]:
    for rx in EP_RE_LIST:
        m = rx.search(name or "")
        if m:
            try:
                n = int(m.group(1))
                if 0 < n < 1000:
                    return n
            except Exception:
                pass
    return None

def extract_season_from_name(name: str) -> Optional[str]:
    m = SEASON_LIKE_RE.search(name or "")
    if m:
        return f"S{int(m.group(1)):02d}"
    return None

def pad_episode(n: int) -> str:
    return f"E{n:02d}"

def safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip()

# ───────────────────────── Filename builder ─────────────────────────
def build_filename_with_rules(
    fmt: str,
    channel: str,
    anime: str,
    orig_name: str,
    extracted_season: Optional[str],
    ep_code: str,
    quality: Optional[str],
) -> str:
    """
    Rules:
    - Replace placeholders: {ChannelName}, {AnimeName}, {Ep}, {Quality}.
    - Season:
      * If format contains literal Sxx (e.g., 'S01'), use it unchanged.
      * Else if format contains {Sn}, replace with extracted season (from filename or default 'S01').
      * Else (no literal Sxx and no {Sn}):
         - Try to inject season before {Ep} if {Ep} exists: replace '{Ep}' with 'Sxx{Ep}'.
         - If no {Ep} in format, prefix 'Sxx ' at start.
    """
    season = extracted_season or "S01"

    out = fmt
    out = out.replace("{ChannelName}", channel)
    out = out.replace("{AnimeName}", anime)
    out = out.replace("{Ep}", ep_code)
    out = out.replace("{Quality}", quality or "")

    if LITERAL_SEASON_IN_FMT_RE.search(out):
        # Literal season present in format -> keep as is
        pass
    elif "{Sn}" in out:
        out = out.replace("{Sn}", season)
    else:
        # No season placeholder; inject season near {Ep} if possible
        if "{Ep}" in fmt:
            # we already replaced {Ep}, so do a pre-injection:
            # put season immediately before the episode code if not already there
            out = out.replace(ep_code, f"{season}{ep_code}", 1)
        else:
            out = f"{season} {out}"

    # Clean multi-spaces
    out = " ".join(out.split())
    return out

# ───────────────────────── Metadata (FFmpeg) ─────────────────────────
def apply_metadata(
    src_path: str,
    dst_path: str,
    *,
    user_meta: Dict[str, Optional[str]],
    title: Optional[str],
    season: Optional[str],
    ep_number: Optional[int],
    thumbnail: Optional[str]
) -> str:
    """
    Fast -c copy remux with injected metadata.
    Always writes a friendly comment; applies user's /metadata values when 'On'.
    """
    cmd = ["ffmpeg", "-y", "-i", src_path]
    if thumbnail and Path(thumbnail).exists():
        cmd += ["-i", thumbnail, "-map", "0", "-map", "1", "-disposition:v:1", "attached_pic"]
    else:
        cmd += ["-map", "0"]

    meta_args: List[str] = []
    meta_args += ["-metadata", f"comment={FIXED_COMMENT}"]
    if title:
        meta_args += ["-metadata", f"title={title}"]
    if season:
        meta_args += ["-metadata", f"season_number={season.lstrip('Ss')}"]
    if ep_number is not None:
        meta_args += ["-metadata", f"episode_id={ep_number}"]

    if user_meta.get("status") == "On":
        if user_meta.get("title"):    meta_args += ["-metadata", f"title={user_meta['title']}"]
        if user_meta.get("author"):   meta_args += ["-metadata", f"author={user_meta['author']}"]
        if user_meta.get("artist"):   meta_args += ["-metadata", f"artist={user_meta['artist']}"]
        if user_meta.get("audio"):    meta_args += ["-metadata", f"audio={user_meta['audio']}"]
        if user_meta.get("subtitle"): meta_args += ["-metadata", f"subtitle={user_meta['subtitle']}"]
        if user_meta.get("video"):    meta_args += ["-metadata", f"video={user_meta['video']}"]

    cmd += meta_args
    cmd += ["-c", "copy", dst_path]

    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return dst_path
    except subprocess.CalledProcessError:
        shutil.copy(src_path, dst_path)
        return dst_path

# ───────────────────────── Download helper ─────────────────────────
async def download_media(msg: Message, dest_dir: Path) -> Tuple[str, str, str]:
    media = msg.video or msg.document or msg.audio or msg.animation or msg.voice
    if not media:
        raise ValueError("Unsupported media type")
    orig_name = getattr(media, "file_name", None) or "file"
    ext = "." + (orig_name.split(".")[-1] if "." in orig_name else "mp4")
    path = await msg.download(file_name=str(dest_dir / orig_name))
    return path, orig_name, ext

# ───────────────────────── Start / Help ─────────────────────────
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(_, m: Message):
    if not is_admin(m.from_user.id):
        return await m.reply_text("❌ This is a private bot.")
    await m.reply_text(
        "**Private Auto-Rename Bot**\n\n"
        "• Manual: reply to a media with `/rename New Name`\n"
        "• Auto: `/auto_rename` → send thumbnail → send format → send episodes → `/rename_it`\n"
        "• Metadata: `/metadata` to view/toggle and `/settitle`, `/setauthor`, `/setartist`, `/setaudio`, `/setsubtitle`, `/setvideo`\n"
        "• Thumbnail: `/add_thumbnail`, `/delete_thumb`\n"
        "• Admin: `/add_admin <id>`, `/remove_admin <id>`, `/list_admins`"
    )

@app.on_message(filters.private & filters.command("help"))
async def help_cmd(_, m: Message):
    if not is_admin(m.from_user.id): return
    await start_cmd(_, m)

# ───────────────────────── Manual rename ─────────────────────────
RENAME_CMD_RE = re.compile(r"^/rename(?:@\w+)?\s+(.+)$", re.IGNORECASE)

@app.on_message(filters.private & filters.command("rename"))
async def manual_rename(_, m: Message):
    if not is_admin(m.from_user.id):
        return await m.reply_text("❌ Private bot. Access denied.")
    if not m.reply_to_message or not (m.reply_to_message.video or m.reply_to_message.document or m.reply_to_message.audio):
        return await m.reply_text("Reply to a video/file with:\n`/rename New File Name`", quote=True)

    match = RENAME_CMD_RE.match(m.text or "")
    if not match:
        return await m.reply_text("Usage:\n`/rename New File Name`", quote=True)

    new_base = safe_name(match.group(1))
    thumb = get_user_thumb(m.from_user.id)
    status = await m.reply_text("⬇️ Downloading…")

    src_path, orig_name, ext = await download_media(m.reply_to_message, TMP_DIR)
    out_path = TMP_DIR / f"{new_base}{ext}"

    meta_pref = get_user_meta(m.from_user.id)
    title = new_base

    if ensure_ffmpeg():
        apply_metadata(
            src_path, str(out_path),
            user_meta=meta_pref, title=title, season=None, ep_number=None, thumbnail=thumb
        )
    else:
        shutil.copy(src_path, out_path)

    # Upload back to user
    if m.reply_to_message.video:
        await m.reply_video(str(out_path), file_name=out_path.name, thumb=thumb, supports_streaming=True, caption=new_base)
    elif m.reply_to_message.audio:
        await m.reply_audio(str(out_path), file_name=out_path.name, caption=new_base)
    else:
        await m.reply_document(str(out_path), file_name=out_path.name, caption=new_base)

    # Log
    if LOG_CHANNEL:
        try:
            cap = f"🛠 Manual rename by {m.from_user.mention}\n**New Name:** `{out_path.name}`"
            if m.reply_to_message.video:
                await app.send_video(LOG_CHANNEL, str(out_path), file_name=out_path.name, thumb=thumb, supports_streaming=True, caption=cap)
            elif m.reply_to_message.audio:
                await app.send_audio(LOG_CHANNEL, str(out_path), file_name=out_path.name, caption=cap)
            else:
                await app.send_document(LOG_CHANNEL, str(out_path), file_name=out_path.name, caption=cap)
        except Exception:
            pass

    await status.edit_text(f"✅ Done: **{out_path.name}**")

    # cleanup
    try:
        Path(src_path).unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)
    except Exception:
        pass

# ───────────────────────── Thumbnails ─────────────────────────
@app.on_message(filters.private & filters.command("add_thumbnail"))
async def add_thumb(_, m: Message):
    if not is_admin(m.from_user.id): return await m.reply_text("❌ Private bot.")
    await m.reply_text("📸 Send me the thumbnail image (reply to this message).")

@app.on_message(filters.private & filters.photo)
async def save_thumb(_, m: Message):
    if not is_admin(m.from_user.id): return
    # If it's part of auto flow, handled there; otherwise save as manual thumb
    path = await m.download(file_name=str(THUMBS_DIR / f"thumb_{m.from_user.id}.jpg"))
    set_user_thumb(m.from_user.id, path)
    await m.reply_text("✅ Thumbnail saved (used for manual & auto).")

@app.on_message(filters.private & filters.command("delete_thumb"))
async def delete_thumb(_, m: Message):
    if not is_admin(m.from_user.id): return
    del_user_thumb(m.from_user.id)
    await m.reply_text("🗑️ Thumbnail deleted.")

# ───────────────────────── Admin management ─────────────────────────
@app.on_message(filters.private & filters.command("add_admin"))
async def add_admin(_, m: Message):
    if not is_owner(m.from_user.id): return
    parts = m.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await m.reply_text("Usage: /add_admin <user_id>")
    uid = int(parts[1])
    if uid != OWNER_ID and uid not in STORE.setdefault("admins", []):
        STORE["admins"].append(uid); save_store()
    await m.reply_text(f"✅ Added admin: {uid}")

@app.on_message(filters.private & filters.command("remove_admin"))
async def remove_admin(_, m: Message):
    if not is_owner(m.from_user.id): return
    parts = m.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await m.reply_text("Usage: /remove_admin <user_id>")
    uid = int(parts[1])
    if uid in STORE.get("admins", []):
        STORE["admins"].remove(uid); save_store()
    await m.reply_text(f"🗑️ Removed admin: {uid}")

@app.on_message(filters.private & filters.command("list_admins"))
async def list_admins(_, m: Message):
    if not is_admin(m.from_user.id): return
    admins = STORE.get("admins", [])
    txt = "👑 Owner: {}\n👤 Admins:\n{}".format(OWNER_ID, "\n".join(map(str, admins)) if admins else "—")
    await m.reply_text(txt)

# ───────────────────────── Metadata Commands (from ZIP idea) ─────────────────────────
def meta_screen(uid: int) -> Tuple[str, InlineKeyboardMarkup]:
    meta = get_user_meta(uid)
    title = meta.get("title") or "Not set"
    author = meta.get("author") or "Not set"
    artist = meta.get("artist") or "Not set"
    audio = meta.get("audio") or "Not set"
    subtitle = meta.get("subtitle") or "Not set"
    video = meta.get("video") or "Not set"
    status = meta.get("status", "Off")

    text = (
        f"**㊋ Your Metadata is currently: {status}**\n\n"
        f"**◈ Title ▹** `{title}`\n"
        f"**◈ Author ▹** `{author}`\n"
        f"**◈ Artist ▹** `{artist}`\n"
        f"**◈ Audio  ▹** `{audio}`\n"
        f"**◈ Subtitle ▹** `{subtitle}`\n"
        f"**◈ Video ▹** `{video}`\n"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"On{' ✅' if status=='On' else ''}", callback_data="meta_on"),
            InlineKeyboardButton(f"Off{' ✅' if status=='Off' else ''}", callback_data="meta_off"),
        ],
        [InlineKeyboardButton("How to Set Metadata", callback_data="meta_info")]
    ])
    return text, kb

@app.on_message(filters.private & filters.command("metadata"))
async def metadata_cmd(_, m: Message):
    if not is_admin(m.from_user.id): return
    text, kb = meta_screen(m.from_user.id)
    await m.reply_text(text, reply_markup=kb, disable_web_page_preview=True)

@app.on_callback_query(filters.regex(r"meta_on|meta_off|meta_info"))
async def metadata_cb(_, q: CallbackQuery):
    uid = q.from_user.id
    if not is_admin(uid):
        return await q.answer("Private bot.", show_alert=True)
    if q.data == "meta_on":
        set_meta_status(uid, "On")
    elif q.data == "meta_off":
        set_meta_status(uid, "Off")
    elif q.data == "meta_info":
        await q.message.edit_text(
            "Use commands:\n"
            "`/settitle ...`, `/setauthor ...`, `/setartist ...`, `/setaudio ...`, `/setsubtitle ...`, `/setvideo ...`\n"
            "Toggle with `/metadata` → On/Off. These tags will be written into your files along with a friendly comment.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Home", callback_data="meta_home"),
                                                InlineKeyboardButton("Close", callback_data="meta_close")]])
        )
        return
    if q.data in ("meta_on", "meta_off"):
        text, kb = meta_screen(uid)
        await q.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    elif q.data == "meta_close":
        with contextlib.suppress(Exception):
            await q.message.delete()
    elif q.data == "meta_home":
        text, kb = meta_screen(uid)
        await q.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)

@app.on_message(filters.private & filters.command('settitle'))
async def settitle(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give title\nExample: `/settitle Encoded By @Animes_Station`")
    set_user_meta(m.from_user.id, "title", m.text.split(" ",1)[1])
    await m.reply_text("✅ Title saved")

@app.on_message(filters.private & filters.command('setauthor'))
async def setauthor(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give author\nExample: `/setauthor @Animes_Station`")
    set_user_meta(m.from_user.id, "author", m.text.split(" ",1)[1])
    await m.reply_text("✅ Author saved")

@app.on_message(filters.private & filters.command('setartist'))
async def setartist(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give artist\nExample: `/setartist @Animes_Station`")
    set_user_meta(m.from_user.id, "artist", m.text.split(" ",1)[1])
    await m.reply_text("✅ Artist saved")

@app.on_message(filters.private & filters.command('setaudio'))
async def setaudio(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give audio title\nExample: `/setaudio AAC 2.0`")
    set_user_meta(m.from_user.id, "audio", m.text.split(" ",1)[1])
    await m.reply_text("✅ Audio saved")

@app.on_message(filters.private & filters.command('setsubtitle'))
async def setsubtitle(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give subtitle title\nExample: `/setsubtitle English`")
    set_user_meta(m.from_user.id, "subtitle", m.text.split(" ",1)[1])
    await m.reply_text("✅ Subtitle saved")

@app.on_message(filters.private & filters.command('setvideo'))
async def setvideo(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give video title\nExample: `/setvideo HEVC 10bit`")
    set_user_meta(m.from_user.id, "video", m.text.split(" ",1)[1])
    await m.reply_text("✅ Video saved")

# ───────────────────────── Auto-rename session ─────────────────────────
class AutoSession:
    def __init__(self):
        self.stage = "idle"           # idle|need_thumb|need_format|collecting
        self.format_str = None
        self.channel_name = ""
        self.anime_name = ""
        self.season_hint = None      # from user (S01), optional
        self.queue: List[int] = []
        self.thumb_path = None
        self.next_ep = 1

SESSIONS: Dict[int, AutoSession] = {}

@app.on_message(filters.private & filters.command("auto_rename"))
async def auto_rename_start(_, m: Message):
    if not is_admin(m.from_user.id): return await m.reply_text("❌ Private bot.")
    s = SESSIONS.setdefault(m.from_user.id, AutoSession())
    s.stage = "need_thumb"
    s.queue.clear()
    s.format_str = None
    s.thumb_path = None
    s.channel_name = ""
    s.anime_name = ""
    s.season_hint = None
    s.next_ep = 1
    await m.reply_text("🔁 Auto-rename started.\nPlease send a **thumbnail image** (required).")

# Session photo (thumbnail) for auto flow
@app.on_message(filters.private & filters.photo)
async def session_thumb_auto(_, m: Message):
    if not is_admin(m.from_user.id): return
    s = SESSIONS.get(m.from_user.id)
    if not s or s.stage != "need_thumb": 
        # handled by global photo handler for manual thumb above
        return
    path = await m.download(file_name=str(THUMBS_DIR / f"session_{m.from_user.id}.jpg"))
    s.thumb_path = path
    s.stage = "need_format"
    await m.reply_text(
        "✅ Thumbnail saved.\nNow send your **filename format** (include literal `[Hindi]` if you want):\n"
        "```\n{ChannelName} {AnimeName} {Sn}{Ep} [Hindi] {Quality}\n```\n"
        "_Rules: If you write literal `S01` in format, it will be used as is. If you use `{Sn}`, bot will substitute from filename. If you omit both, bot will inject season extracted from filename._",
    )

# Capture format / details while collecting
BLOCKED_CMDS = ["rename","auto_rename","rename_it","cancel","metadata","settitle","setauthor","setartist","setaudio","setsubtitle","setvideo","add_thumbnail","delete_thumb","add_admin","remove_admin","list_admins","start","help"]
@app.on_message(filters.private & filters.text & ~filters.command(BLOCKED_CMDS))
async def session_text(_, m: Message):
    if not is_admin(m.from_user.id): return
    s = SESSIONS.get(m.from_user.id)
    if not s: return
    if s.stage == "need_format":
        s.format_str = m.text.strip()
        s.stage = "collecting"
        await m.reply_text(
            "✅ Format saved.\nSend me **Channel Name**, then **Anime Name**, then (optional) **Season** like `S01`.\n"
            "After that, start sending episodes (videos/files). When done: `/rename_it`."
        )
        return
    if s.stage == "collecting":
        txt = m.text.strip()
        if not s.channel_name:
            s.channel_name = txt
            return await m.reply_text(f"📡 Channel set: **{s.channel_name}**")
        if not s.anime_name:
            s.anime_name = txt
            return await m.reply_text(f"🎬 Anime set: **{s.anime_name}**")
        if s.season_hint is None and txt.upper().startswith("S") and len(txt) <= 4:
            s.season_hint = txt.upper()
            return await m.reply_text(f"🗂️ Season set: **{s.season_hint}**")

# Collect media to queue
RENAMABLE = filters.video | filters.document | filters.audio | filters.animation
@app.on_message(filters.private & RENAMABLE)
async def collect_media(_, m: Message):
    if not is_admin(m.from_user.id): return
    s = SESSIONS.get(m.from_user.id)
    if not s: return
    if s.stage == "need_thumb":
        return await m.reply_text("⚠️ Send a **photo** thumbnail first.")
    if s.stage in ("need_format","collecting"):
        s.queue.append(m.id)
        name = getattr((m.video or m.document or m.audio), "file_name", "") or ""
        ep_num = extract_episode(name) or s.next_ep
        if extract_episode(name) is None:
            s.next_ep += 1
        await m.reply_text(f"🧾 Queued ({pad_episode(ep_num)}). Send more or `/rename_it` to start.")

@app.on_message(filters.private & filters.command("cancel"))
async def auto_cancel(_, m: Message):
    SESSIONS.pop(m.from_user.id, None)
    await m.reply_text("❌ Session cancelled.")

@app.on_message(filters.private & filters.command("rename_it"))
async def auto_rename_go(_, m: Message):
    if not is_admin(m.from_user.id): return await m.reply_text("❌ Private bot.")
    s = SESSIONS.get(m.from_user.id)
    if not s or s.stage not in ("need_format","collecting"):
        return await m.reply_text("⚠️ No active session. Use `/auto_rename`.")
    if not s.thumb_path:  # required by your rule
        return await m.reply_text("📸 Please send a **thumbnail** first.")
    if not s.format_str:
        return await m.reply_text("✍️ Please send a **filename format** first.")
    if not s.channel_name or not s.anime_name:
        return await m.reply_text("ℹ️ Send **Channel Name** and **Anime Name** first.")

    await m.reply_text("🚀 Starting batch…")
    meta_pref = get_user_meta(m.from_user.id)

    for mid in s.queue:
        try:
            msg = await app.get_messages(m.chat.id, mid)
            src_path, orig_name, ext = await download_media(msg, TMP_DIR)

            # Episode number
            ep_num = extract_episode(orig_name) or s.next_ep
            if extract_episode(orig_name) is None:
                s.next_ep += 1
            ep_code = pad_episode(ep_num)

            # Season extraction preference:
            # 1) User season hint (S01) overrides extraction if {Sn} used or if need to inject
            # 2) Else extract from filename
            season_from_name = extract_season_from_name(orig_name)
            season_effective = s.season_hint or season_from_name or "S01"

            # Quality
            ql = detect_quality_from_filename(orig_name)
            if not ql:
                h = probe_height(src_path)
                ql = quality_from_height(h) or "Unknown"

            # Build new base name with rules
            new_base = build_filename_with_rules(
                fmt=s.format_str,
                channel=s.channel_name,
                anime=s.anime_name,
                orig_name=orig_name,
                extracted_season=season_effective,
                ep_code=ep_code,
                quality=ql
            )
            new_base = safe_name(new_base)
            out_path = TMP_DIR / f"{new_base}{ext}"

            # Apply metadata + thumb cover
            if ensure_ffmpeg():
                apply_metadata(
                    src_path, str(out_path),
                    user_meta=meta_pref, title=new_base,
                    season=season_effective, ep_number=ep_num,
                    thumbnail=s.thumb_path
                )
            else:
                shutil.copy(src_path, out_path)

            # Upload back to user
            caption = f"{new_base}\n\n📥 {ep_code} • {ql}"
            media = msg.video or msg.document or msg.audio
            if msg.video:
                await m.reply_video(str(out_path), file_name=out_path.name, thumb=s.thumb_path, supports_streaming=True, caption=caption)
            elif msg.audio:
                await m.reply_audio(str(out_path), file_name=out_path.name, caption=caption)
            else:
                await m.reply_document(str(out_path), file_name=out_path.name, caption=caption)

            # Log channel
            if LOG_CHANNEL:
                try:
                    log_cap = (f"🌀 Auto Rename by {m.from_user.mention}\n"
                               f"**Original:** `{orig_name}`\n**New:** `{out_path.name}`\n"
                               f"**Ep:** {ep_code} • **Quality:** {ql}")
                    if msg.video:
                        await app.send_video(LOG_CHANNEL, str(out_path), file_name=out_path.name, thumb=s.thumb_path, supports_streaming=True, caption=log_cap)
                    elif msg.audio:
                        await app.send_audio(LOG_CHANNEL, str(out_path), file_name=out_path.name, caption=log_cap)
                    else:
                        await app.send_document(LOG_CHANNEL, str(out_path), file_name=out_path.name, caption=log_cap)
                except Exception:
                    pass

            # cleanup each file
            try:
                Path(src_path).unlink(missing_ok=True)
                Path(out_path).unlink(missing_ok=True)
            except Exception:
                pass

        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            try:
                await m.reply_text(f"❌ Error while processing `{orig_name}`: `{e}`")
            except Exception:
                pass

    await m.reply_text("✅ Batch finished.")
    # End session
    SESSIONS.pop(m.from_user.id, None)

# ───────────────────────── Run ─────────────────────────
if __name__ == "__main__":
    print("🚀 Bot is running…")
    app.run()
