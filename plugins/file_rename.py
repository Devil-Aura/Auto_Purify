import os
import re
import time
import shutil
import asyncio
import logging
from datetime import datetime, timedelta
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from plugins.antinsfw import check_anti_nsfw
from helper.utils import progress_for_pyrogram, humanbytes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global dictionary to track ongoing operations
renaming_operations = {}

# Enhanced regex patterns for season and episode extraction
SEASON_EPISODE_PATTERNS = [
    (re.compile(r"S(\d+)(?:E|EP)(\d+)"), ("season", "episode")),
    (re.compile(r"S(\d+)[\s-]*(?:E|EP)(\d+)"), ("season", "episode")),
    (re.compile(r"Season\s*(\d+)\s*Episode\s*(\d+)", re.IGNORECASE), ("season", "episode")),
    (re.compile(r"\[S(\d+)\]\[E(\d+)\]"), ("season", "episode")),
    (re.compile(r"S(\d+)[^\d]*(\d+)"), ("season", "episode")),
    (re.compile(r"(?:E|EP|Episode)\s*(\d+)", re.IGNORECASE), (None, "episode")),
    (re.compile(r"\b(\d+)\b"), (None, "episode"))
]

# Quality detection patterns
QUALITY_PATTERNS = [
    (re.compile(r"\b(\d{3,4}[pi])\b", re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r"\b(4k|2160p)\b", re.IGNORECASE), lambda m: "4k"),
    (re.compile(r"\b(2k|1440p)\b", re.IGNORECASE), lambda m: "2k"),
    (re.compile(r"\b(HDRip|HDTV)\b", re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r"\b(4kX264|4kx265)\b", re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r"\[(\d{3,4}[pi])\]", re.IGNORECASE), lambda m: m.group(1)),
]


def extract_season_episode(filename):
    """Extract season and episode numbers from filename"""
    for pattern, (season_group, episode_group) in SEASON_EPISODE_PATTERNS:
        match = pattern.search(filename)
        if match:
            season = match.group(1) if season_group else None
            episode = match.group(2) if episode_group else match.group(1)
            return season, episode
    return None, None


def extract_quality(filename):
    """Extract quality information from filename"""
    for pattern, extractor in QUALITY_PATTERNS:
        match = pattern.search(filename)
        if match:
            return extractor(match)
    return "Unknown"


async def cleanup_files(*paths):
    """Safely remove files if they exist"""
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Error removing {path}: {e}")


async def process_thumbnail(thumb_path):
    """Resize thumbnail image"""
    if not thumb_path or not os.path.exists(thumb_path):
        return None
    try:
        with Image.open(thumb_path) as img:
            img = img.convert("RGB").resize((320, 320))
            img.save(thumb_path, "JPEG")
        return thumb_path
    except Exception as e:
        logger.error(f"Thumbnail processing failed: {e}")
        await cleanup_files(thumb_path)
        return None


def get_file_duration(file_path):
    """Get duration of media file"""
    try:
        metadata = extractMetadata(createParser(file_path))
        if metadata is not None and metadata.has("duration"):
            return str(timedelta(seconds=int(metadata.get("duration").seconds)))
        return "00:00:00"
    except Exception:
        return "00:00:00"


def format_caption(filename, filesize, duration):
    """Simple caption format"""
    return f"**{filename}**\n\n📦 Size: {humanbytes(filesize)}\n⏳ Duration: {duration}\n\n⚡ @World_Fastest_Bots"


@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message: Message):
    """Main handler for auto-renaming files"""
    user_id = message.from_user.id

    # Get file information
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_size = message.document.file_size
        media_type = "document"
    elif message.video:
        file_id = message.video.file_id
        file_name = message.video.file_name or "video"
        file_size = message.video.file_size
        media_type = "video"
    elif message.audio:
        file_id = message.audio.file_id
        file_name = message.audio.file_name or "audio"
        file_size = message.audio.file_size
        media_type = "audio"
    else:
        return await message.reply_text("Unsupported file type ❌")

    # NSFW check
    if await check_anti_nsfw(file_name, message):
        return await message.reply_text("NSFW content detected ❌")

    # Prevent duplicate processing
    if file_id in renaming_operations:
        if (datetime.now() - renaming_operations[file_id]).seconds < 10:
            return
    renaming_operations[file_id] = datetime.now()

    # File paths
    download_path = None
    thumb_path = None

    try:
        # Extract metadata from filename
        season, episode = extract_season_episode(file_name)
        quality = extract_quality(file_name)

        # New filename format
        ext = os.path.splitext(file_name)[1] or (".mp4" if media_type == "video" else ".mp3")
        new_filename = f"Series_S{season or 'XX'}E{episode or 'XX'}_{quality}{ext}"
        download_path = f"downloads/{new_filename}"

        os.makedirs(os.path.dirname(download_path), exist_ok=True)

        # Download
        msg = await message.reply_text("**⬇️ Downloading...**")
        file_path = await client.download_media(
            message,
            file_name=download_path,
            progress=progress_for_pyrogram,
            progress_args=("Downloading...", msg, time.time())
        )

        # Duration
        duration = "00:00:00"
        if media_type in ["video", "audio"]:
            duration = get_file_duration(file_path)

        # Caption
        caption = format_caption(new_filename, file_size, duration)

        # Upload
        await msg.edit("**⬆️ Uploading...**")
        try:
            if media_type == "document":
                await client.send_document(message.chat.id, file_path, caption=caption)
            elif media_type == "video":
                await client.send_video(message.chat.id, file_path, caption=caption)
            elif media_type == "audio":
                await client.send_audio(message.chat.id, file_path, caption=caption)
            await msg.delete()
        except Exception as e:
            await msg.edit(f"Upload failed: {e}")
            raise

    except Exception as e:
        logger.error(f"Processing error: {e}")
        await message.reply_text(f"Error: {str(e)}")
    finally:
        await cleanup_files(download_path, thumb_path)
        renaming_operations.pop(file_id, None)
