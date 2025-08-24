import os
import re
import json
import asyncio
import shutil
import subprocess
import time
import contextlib
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
from pyrogram.enums import ParseMode

# ───────────────────────── CONFIG ─────────────────────────
API_ID = int(os.getenv("API_ID", "22768311"))
API_HASH = os.getenv("API_HASH", "702d8884f48b42e865425391432b3794"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT-YOUR-BOT-TOKEN-HERE")
OWNER_ID = int(os.getenv("OWNER_ID", "6040503076"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1003058967184"))

# Default metadata text (applied to title/audio/subtitle if user metadata is Off or empty)
METADATA_TEXT = "@CrunchyRollChannel For More Animes In Hindi!"

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
    re.compile(r"\bEp(?:isode)?\s*[-_. ]*(\d{1,3})\b", re.IGNORECASE),
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
    q = m.group(1) if m else None
    if q:
        q = q.upper().replace("2K", "1440p").replace("4K", "2160p")
    return q

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
    if h >= 2000: return "2160p"
    if h >= 1400: return "1440p"
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
    Season rules:
      - Literal Sxx in format -> keep as is.
      - If {Sn} in format -> replace with extracted season (from filename or 'S01').
      - Else -> inject season before {Ep} (or prefix if {Ep} absent).
    """
    season = extracted_season or "S01"
    out = fmt
    out = out.replace("{ChannelName}", channel)
    out = out.replace("{AnimeName}", anime)
    out = out.replace("{Ep}", ep_code)
    out = out.replace("{Quality}", quality or "")

    if LITERAL_SEASON_IN_FMT_RE.search(out):
        pass
    elif "{Sn}" in out:
        out = out.replace("{Sn}", season)
    else:
        # inject near episode if possible
        if ep_code in out:
            out = out.replace(ep_code, f"{season}{ep_code}", 1)
        else:
            out = f"{season} {out}"

    out = " ".join(out.split())
    return out

# ───────────────────────── Metadata (FFmpeg) ─────────────────────────
def resolve_effective_meta(user_meta: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """
    Build the final metadata dict:
      - If user toggled On and set fields, use them.
      - Otherwise use default METADATA_TEXT for 'title', 'audio', 'subtitle' only.
      - No 'comment' field is ever written.
    """
    on = user_meta.get("status") == "On"
    title = (user_meta.get("title") if on and user_meta.get("title") else METADATA_TEXT)
    audio = (user_meta.get("audio") if on and user_meta.get("audio") else METADATA_TEXT)
    subtitle = (user_meta.get("subtitle") if on and user_meta.get("subtitle") else METADATA_TEXT)
    # Optional fields (won't be forced):
    author = user_meta.get("author") if on and user_meta.get("author") else None
    artist = user_meta.get("artist") if on and user_meta.get("artist") else None
    video  = user_meta.get("video")  if on and user_meta.get("video")  else None
    return {
        "title": title,
        "audio": audio,
        "subtitle": subtitle,
        "author": author,
        "artist": artist,
        "video": video
    }

def apply_metadata(
    src_path: str,
    dst_path: str,
    *,
    user_meta: Dict[str, Optional[str]],
    computed_title: Optional[str],
    season: Optional[str],
    ep_number: Optional[int],
    thumbnail: Optional[str]
) -> str:
    """
    Fast -c copy remux with injected metadata.
    - No comment tag.
    - Writes +faststart to fix 0:00 & improve streaming.
    - Attaches thumbnail as cover (doesn't replace v:0).
    """
    eff = resolve_effective_meta(user_meta)

    cmd = ["ffmpeg", "-y", "-i", src_path]
    if thumbnail and Path(thumbnail).exists():
        cmd += ["-i", thumbnail, "-map", "0", "-map", "1", "-disposition:v:1", "attached_pic"]
    else:
        cmd += ["-map", "0"]

    meta_args: List[str] = []

    # Computed per-file title (filename) wins; if not provided, fall back to eff['title']
    if computed_title:
        meta_args += ["-metadata", f"title={computed_title}"]
    elif eff["title"]:
        meta_args += ["-metadata", f"title={eff['title']}"]

    # Optional extras if present
    if eff["author"]:   meta_args += ["-metadata", f"author={eff['author']}"]
    if eff["artist"]:   meta_args += ["-metadata", f"artist={eff['artist']}"]
    if eff["video"]:    meta_args += ["-metadata", f"video={eff['video']}"]

    # Always set audio/subtitle titles to the text (user/custom or default)
    if eff["audio"]:    meta_args += ["-metadata", f"audio={eff['audio']}"]
    if eff["subtitle"]: meta_args += ["-metadata", f"subtitle={eff['subtitle']}"]

    if season:
        meta_args += ["-metadata", f"season_number={season.lstrip('Ss')}"]
    if ep_number is not None:
        meta_args += ["-metadata", f"episode_id={ep_number}"]

    cmd += meta_args
    cmd += ["-c", "copy", "-movflags", "+faststart", dst_path]

    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return dst_path
    except subprocess.CalledProcessError:
        shutil.copy(src_path, dst_path)
        return dst_path

# ───────────────────────── Progress (anti-flood) ─────────────────────────
_PROGRESS_STATE: Dict[int, Dict[str, float]] = {}  # msg_id -> {"t": last_ts, "p": last_percent}

async def progress_cb(current: int, total: int, status_msg: Message, label: str):
    try:
        msg_id = status_msg.id
        now = time.time()
        state = _PROGRESS_STATE.setdefault(msg_id, {"t": 0.0, "p": -1.0})
        percent = 0.0 if total == 0 else (current * 100 / total)

        # throttle: 1s or +1%
        if (now - state["t"] < 1.0) and (percent - state["p"] < 1.0):
            return

        state["t"] = now
        state["p"] = percent

        filled = int(percent // 10)
        bar = "█" * filled + "░" * (10 - filled)
        txt = f"{label}\n[{bar}] {percent:.1f}%\n{current/1024/1024:.1f}MB / {total/1024/1024:.1f}MB"
        with contextlib.suppress(FloodWait, Exception):
            await status_msg.edit_text(txt)
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception:
        pass

# ───────────────────────── Download helper ─────────────────────────
async def download_media(msg: Message, dest_dir: Path, status: Optional[Message]=None) -> Tuple[str, str, str]:
    media = msg.video or msg.document or msg.audio or msg.animation or msg.voice
    if not media:
        raise ValueError("Unsupported media type")
    orig_name = getattr(media, "file_name", None) or "file"
    # unique name to avoid .temp collisions
    unique_name = f"{msg.id}_{orig_name}"
    ext = "." + (orig_name.split(".")[-1] if "." in orig_name else "mp4")
    target_path = str(dest_dir / unique_name)
    path = await msg.download(
        file_name=target_path,
        progress=progress_cb if status else None,
        progress_args=(status, "📥 Downloading...") if status else None
    )
    return path, orig_name, ext

# ───────────────────────── Start / Help ─────────────────────────
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(_, m: Message):
    if not is_admin(m.from_user.id):
        return await m.reply_text("❌ This is a private bot.")
    await m.reply_text(
        "**Private Auto-Rename Bot**\n\n"
        "• Manual: reply to a media with `/rename New File Name`\n"
        "• Auto: `/auto_rename` → send thumbnail → send format → send episodes → `/rename_it`\n"
        "• Metadata: `/metadata` to view/toggle and `/settitle`, `/setauthor`, `/setartist`, `/setaudio`, `/setsubtitle`, `/setvideo`\n"
        "• Thumbnail: `/add_thumbnail`, `/delete_thumb`\n"
        "• Admin: `/add_admin <id>`, `/remove_admin <id>`, `/list_admins`",
        parse_mode=ParseMode.MARKDOWN
    )

@app.on_message(filters.private & filters.command("help"))
async def help_cmd(_, m: Message):
    if not is_admin(m.from_user.id): return
    await start_cmd(_, m)

# ───────────────────────── Manual rename ─────────────────────────
RENAME_CMD_RE = re.compile(r"^/rename(?:@\w+)?\s+(.+)$", re.IGNORECASE)

async def _send_to_chat_and_log(m: Message, path: Path, thumb: Optional[str]):
    caption = f"**{path.name}**"
    # send back to user
    if m.reply_to_message.video:
        await m.reply_video(
            str(path), file_name=path.name, thumb=thumb, supports_streaming=True,
            caption=caption, parse_mode=ParseMode.MARKDOWN,
            progress=progress_cb, progress_args=(await m.reply_text("📤 Preparing upload…"), "📤 Uploading...")
        )
    elif m.reply_to_message.audio:
        await m.reply_audio(
            str(path), file_name=path.name,
            caption=caption, parse_mode=ParseMode.MARKDOWN,
            progress=progress_cb, progress_args=(await m.reply_text("📤 Preparing upload…"), "📤 Uploading...")
        )
    else:
        await m.reply_document(
            str(path), file_name=path.name,
            caption=caption, parse_mode=ParseMode.MARKDOWN,
            progress=progress_cb, progress_args=(await m.reply_text("📤 Preparing upload…"), "📤 Uploading...")
        )

    # Log channel: only the file with only bold filename as caption (no extras)
    if LOG_CHANNEL:
        try:
            if m.reply_to_message.video:
                await app.send_video(LOG_CHANNEL, str(path), file_name=path.name, supports_streaming=True,
                                     caption=caption, parse_mode=ParseMode.MARKDOWN)
            elif m.reply_to_message.audio:
                await app.send_audio(LOG_CHANNEL, str(path), file_name=path.name,
                                     caption=caption, parse_mode=ParseMode.MARKDOWN)
            else:
                await app.send_document(LOG_CHANNEL, str(path), file_name=path.name,
                                        caption=caption, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

@app.on_message(filters.private & filters.command("rename"))
async def manual_rename(_, m: Message):
    if not is_admin(m.from_user.id):
        return await m.reply_text("❌ Private bot. Access denied.")
    if not m.reply_to_message or not (m.reply_to_message.video or m.reply_to_message.document or m.reply_to_message.audio):
        return await m.reply_text("Reply to a video/file with:\n`/rename New File Name`", quote=True, parse_mode=ParseMode.MARKDOWN)

    match = RENAME_CMD_RE.match(m.text or "")
    if not match:
        return await m.reply_text("Usage:\n`/rename New File Name`", quote=True, parse_mode=ParseMode.MARKDOWN)

    new_base = safe_name(match.group(1))
    thumb = get_user_thumb(m.from_user.id)
    status = await m.reply_text("⬇️ Starting…")

    src_path, orig_name, ext = await download_media(m.reply_to_message, TMP_DIR, status)
    out_path = TMP_DIR / f"{new_base}{ext}"

    meta_pref = get_user_meta(m.from_user.id)
    computed_title = new_base

    if ensure_ffmpeg():
        apply_metadata(
            src_path, str(out_path),
            user_meta=meta_pref, computed_title=computed_title,
            season=None, ep_number=None, thumbnail=thumb
        )
    else:
        shutil.copy(src_path, out_path)

    await status.edit_text("✅ Renamed. Uploading…")
    await _send_to_chat_and_log(m, out_path, thumb)

    # cleanup
    with contextlib.suppress(Exception):
        Path(src_path).unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)

# ───────────────────────── Thumbnails ─────────────────────────
@app.on_message(filters.private & filters.command("add_thumbnail"))
async def add_thumb(_, m: Message):
    if not is_admin(m.from_user.id): return await m.reply_text("❌ Private bot.")
    await m.reply_text("📸 Send me the thumbnail image (reply to this message).")

@app.on_message(filters.private & filters.photo)
async def save_thumb(_, m: Message):
    if not is_admin(m.from_user.id): return
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
    await m.reply_text(text, reply_markup=kb, disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)

@app.on_callback_query(filters.regex(r"meta_on|meta_off|meta_info|meta_home|meta_close"))
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
            "Toggle with `/metadata` → On/Off. No footer is added; tags are embedded.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Home", callback_data="meta_home"),
                                                InlineKeyboardButton("Close", callback_data="meta_close")]]),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    elif q.data == "meta_close":
        with contextlib.suppress(Exception):
            await q.message.delete()
        return
    # meta_home or toggle
    text, kb = meta_screen(uid)
    await q.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.private & filters.command('settitle'))
async def settitle(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give title\nExample: `/settitle Encoded By @Animes_Station`", parse_mode=ParseMode.MARKDOWN)
    set_user_meta(m.from_user.id, "title", m.text.split(" ",1)[1])
    await m.reply_text("✅ Title saved")

@app.on_message(filters.private & filters.command('setauthor'))
async def setauthor(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give author\nExample: `/setauthor @Animes_Station`", parse_mode=ParseMode.MARKDOWN)
    set_user_meta(m.from_user.id, "author", m.text.split(" ",1)[1])
    await m.reply_text("✅ Author saved")

@app.on_message(filters.private & filters.command('setartist'))
async def setartist(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give artist\nExample: `/setartist @Animes_Station`", parse_mode=ParseMode.MARKDOWN)
    set_user_meta(m.from_user.id, "artist", m.text.split(" ",1)[1])
    await m.reply_text("✅ Artist saved")

@app.on_message(filters.private & filters.command('setaudio'))
async def setaudio(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give audio title\nExample: `/setaudio AAC 2.0`", parse_mode=ParseMode.MARKDOWN)
    set_user_meta(m.from_user.id, "audio", m.text.split(" ",1)[1])
    await m.reply_text("✅ Audio saved")

@app.on_message(filters.private & filters.command('setsubtitle'))
async def setsubtitle(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give subtitle title\nExample: `/setsubtitle English`", parse_mode=ParseMode.MARKDOWN)
    set_user_meta(m.from_user.id, "subtitle", m.text.split(" ",1)[1])
    await m.reply_text("✅ Subtitle saved")

@app.on_message(filters.private & filters.command('setvideo'))
async def setvideo(_, m: Message):
    if not is_admin(m.from_user.id): return
    if len(m.command) == 1:
        return await m.reply_text("Give video title\nExample: `/setvideo HEVC 10bit`", parse_mode=ParseMode.MARKDOWN)
    set_user_meta(m.from_user.id, "video", m.text.split(" ",1)[1])
    await m.reply_text("✅ Video saved")

# ───────────────────────── Auto-rename session ─────────────────────────
class AutoSession:
    def __init__(self):
        self.stage = "idle"           # idle|need_thumb|need_format|collecting
        self.format_str = None
        self.channel_name = ""
        self.anime_name = ""
        self.season_hint = None       # Optional "S01" typed by user
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

# Session photo (thumbnail)
@app.on_message(filters.private & filters.photo)
async def session_thumb(_, m: Message):
    if not is_admin(m.from_user.id): return
    s = SESSIONS.get(m.from_user.id)
    if not s or s.stage != "need_thumb": 
        return  # regular /add_thumbnail handler already saved
    path = await m.download(file_name=str(THUMBS_DIR / f"session_{m.from_user.id}.jpg"))
    s.thumb_path = path
    s.stage = "need_format"
    await m.reply_text(
        "✅ Thumbnail saved.\nNow send your **filename format**:\n"
        "```\n{ChannelName} {AnimeName} {Sn}{Ep} [Hindi] {Quality}\n```\n"
        "_If you write a literal like `S01`, it will be used as-is. `{Sn}` will be auto-filled from filename._",
        parse_mode=ParseMode.MARKDOWN
    )

# Capture format / details while collecting
@app.on_message(filters.private & filters.text & ~filters.command([
    "rename","auto_rename","rename_it","cancel","metadata",
    "settitle","setauthor","setartist","setaudio","setsubtitle","setvideo",
    "add_thumbnail","delete_thumb","add_admin","remove_admin","list_admins"
]))
async def session_text(_, m: Message):
    if not is_admin(m.from_user.id): return
    s = SESSIONS.get(m.from_user.id)
    if not s: return
    if s.stage == "need_format":
        s.format_str = m.text.strip()
        s.stage = "collecting"
        await m.reply_text(
            "✅ Format saved.\nSend **Channel Name**, then **Anime Name**, then optional **Season** like `S01`.\n"
            "After that, start sending episodes (videos/files). When done: `/rename_it`.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if s.stage == "collecting":
        txt = m.text.strip()
        if not s.channel_name:
            s.channel_name = txt
            return await m.reply_text(f"📡 Channel set: **{s.channel_name}**", parse_mode=ParseMode.MARKDOWN)
        if not s.anime_name:
            s.anime_name = txt
            return await m.reply_text(f"🎬 Anime set: **{s.anime_name}**", parse_mode=ParseMode.MARKDOWN)
        if s.season_hint is None and txt.upper().startswith("S") and len(txt) <= 4:
            s.season_hint = txt.upper()
            return await m.reply_text(f"🗂️ Season set: **{s.season_hint}**", parse_mode=ParseMode.MARKDOWN)

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
        await m.reply_text(f"🧾 Queued ({pad_episode(ep_num)}). Send more or `/rename_it` to start.", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.private & filters.command("cancel"))
async def auto_cancel(_, m: Message):
    SESSIONS.pop(m.from_user.id, None)
    await m.reply_text("❌ Session cancelled.")

@app.on_message(filters.private & filters.command("rename_it"))
async def auto_rename_go(_, m: Message):
    if not is_admin(m.from_user.id): return await m.reply_text("❌ Private bot.")
    s = SESSIONS.get(m.from_user.id)
    if not s or s.stage not in ("need_format","collecting"):
        return await m.reply_text("⚠️ No active session. Use `/auto_rename`.", parse_mode=ParseMode.MARKDOWN)
    if not s.thumb_path:
        return await m.reply_text("📸 Please send a **thumbnail** first.")
    if not s.format_str:
        return await m.reply_text("✍️ Please send a **filename format** first.")
    if not s.channel_name or not s.anime_name:
        return await m.reply_text("ℹ️ Send **Channel Name** and **Anime Name** first.", parse_mode=ParseMode.MARKDOWN)

    meta_pref = get_user_meta(m.from_user.id)
    await m.reply_text("🚀 Starting batch…")

    for mid in list(s.queue):
        try:
            msg = await app.get_messages(m.chat.id, mid)
            status = await m.reply_text("⬇️ Starting…")
            src_path, orig_name, ext = await download_media(msg, TMP_DIR, status)

            # episode number
            ep_num = extract_episode(orig_name) or s.next_ep
            if extract_episode(orig_name) is None:
                s.next_ep += 1
            ep_code = pad_episode(ep_num)

            # season (hint or from filename)
            extracted_season = s.season_hint or extract_season_from_name(orig_name)

            # quality
            ql = detect_quality_from_filename(orig_name)
            if not ql:
                h = probe_height(src_path)
                ql = quality_from_height(h)

            # filename
            new_base = build_filename_with_rules(
                s.format_str, s.channel_name, s.anime_name, orig_name,
                extracted_season, ep_code, ql
            )
            out_path = TMP_DIR / f"{safe_name(new_base)}{ext}"

            # metadata + fast remux
            if ensure_ffmpeg():
                apply_metadata(
                    src_path, str(out_path),
                    user_meta=meta_pref, computed_title=new_base,
                    season=extracted_season, ep_number=ep_num, thumbnail=s.thumb_path
                )
            else:
                shutil.copy(src_path, out_path)

            await status.edit_text("✅ Renamed. Uploading…")
            # send to user & log with only bold filename as caption
            # build a fake wrapper message with video field existence matching original
            wrapper = m
            wrapper.reply_to_message = msg  # so _send_to_chat_and_log knows which type to use (video/audio/document)
            await _send_to_chat_and_log(wrapper, out_path, s.thumb_path)

        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            with contextlib.suppress(Exception):
                await m.reply_text(f"❌ Error: {e}")
        finally:
            with contextlib.suppress(Exception):
                Path(src_path).unlink(missing_ok=True)
                out_path.unlink(missing_ok=True)

    s.queue.clear()
    await m.reply_text("✅ Batch finished.")

# ───────────────────────── RUN ─────────────────────────
if __name__ == "__main__":
    print("🚀 Bot is running…")
    app.run()
