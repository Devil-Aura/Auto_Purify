import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
import re
from collections import defaultdict
from datetime import datetime
from config import Config

# ---------------- In-memory stores ----------------
ACTIVE_SEQUENCES = {}  # user_id -> {"files": [...], "started_at": datetime}
USERS_SEQUENCE_STATS = defaultdict(lambda: {"files_sequenced": 0, "username": "Unknown"})

# Patterns for extracting episode numbers
patterns = [
    re.compile(r'\b(?:EP|E)\s*-\s*(\d{1,3})\b', re.IGNORECASE),
    re.compile(r'\b(?:EP|E)\s*(\d{1,3})\b', re.IGNORECASE),
    re.compile(r'S(\d+)(?:E|EP)(\d+)', re.IGNORECASE),
    re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)\s*(\d+)', re.IGNORECASE),
    re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)', re.IGNORECASE),
    re.compile(r'(?:EP|E)?\s*[-]?\s*(\d{1,3})', re.IGNORECASE),
    re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE),
    re.compile(r'(\d+)')
]

def extract_episode_number(filename):
    """Extract episode number from filename for sorting"""
    for pattern in patterns:
        match = pattern.search(filename)
        if match:
            return int(match.groups()[-1])
    return float('inf')

def is_in_sequence_mode(user_id):
    """Check if user is in sequence mode"""
    return user_id in ACTIVE_SEQUENCES

@Client.on_message(filters.private & filters.command("startsequence"))
async def start_sequence(client, message):
    user_id = message.from_user.id

    if is_in_sequence_mode(user_id):
        await message.reply_text("⚠️ Sequence mode is already active. Send your files or use /endsequence.")
        return

    ACTIVE_SEQUENCES[user_id] = {
        "files": [],
        "started_at": datetime.now()
    }
    await message.reply_text("✅ Sequence mode started! Send your files now.")

@Client.on_message(filters.private & filters.command("endsequence"))
async def end_sequence(client, message):
    user_id = message.from_user.id

    sequence_data = ACTIVE_SEQUENCES.get(user_id)
    if not sequence_data or not sequence_data.get("files"):
        await message.reply_text("❌ No files in sequence!")
        return

    files = sequence_data.get("files", [])
    sorted_files = sorted(files, key=lambda x: extract_episode_number(x["filename"]))
    total = len(sorted_files)
    progress = await message.reply_text(f"⏳ Processing and sorting {total} files...")

    sent_count = 0
    for i, file in enumerate(sorted_files, 1):
        try:
            await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=file["chat_id"],
                message_id=file["msg_id"]
            )
            sent_count += 1
            if i % 5 == 0:
                await progress.edit_text(f"📤 Sent {i}/{total} files...")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error sending file: {e}")

    USERS_SEQUENCE_STATS[user_id]["files_sequenced"] += sent_count
    USERS_SEQUENCE_STATS[user_id]["username"] = message.from_user.first_name

    ACTIVE_SEQUENCES.pop(user_id, None)
    await progress.edit_text(f"✅ Successfully sent {sent_count} files in sequence!")

# Ensure this handler runs before any rename logic
@Client.on_message(filters.private & (filters.document | filters.video | filters.audio), group=0)
async def sequence_file_handler(client, message):
    user_id = message.from_user.id

    if is_in_sequence_mode(user_id):
        if message.document:
            file_name = message.document.file_name
        elif message.video:
            file_name = message.video.file_name or "video"
        elif message.audio:
            file_name = message.audio.file_name or "audio"
        else:
            file_name = "Unknown"

        file_info = {
            "filename": file_name,
            "msg_id": message.id,
            "chat_id": message.chat.id,
            "added_at": datetime.now()
        }

        ACTIVE_SEQUENCES[user_id]["files"].append(file_info)
        message.stop_propagation()
        await message.reply_text(f"📂 Added to sequence: {file_name}")

@Client.on_message(filters.private & filters.command("cancelsequence"))
async def cancel_sequence(client, message):
    user_id = message.from_user.id
    removed = ACTIVE_SEQUENCES.pop(user_id, None)
    if removed:
        await message.reply_text("❌ Sequence mode cancelled. All queued files have been cleared.")
    else:
        await message.reply_text("❓ No active sequence found to cancel.")

@Client.on_message(filters.private & filters.command("showsequence"))
async def show_sequence(client, message):
    user_id = message.from_user.id
    sequence_data = ACTIVE_SEQUENCES.get(user_id)

    if not sequence_data or not sequence_data.get("files"):
        await message.reply_text("No files in current sequence.")
        return

    files = sequence_data.get("files", [])
    sorted_files = sorted(files, key=lambda x: extract_episode_number(x["filename"]))

    file_list = "\n".join([f"{i}. {file['filename']}" for i, file in enumerate(sorted_files, 1)])
    if len(file_list) > 4000:
        file_list = file_list[:3900] + "\n\n... (list truncated)"

    await message.reply_text(f"**Current Sequence Files ({len(files)}):**\n\n{file_list}")

@Client.on_message(filters.command("leaderboard"))
async def leaderboard(client, message):
    top_users = sorted(USERS_SEQUENCE_STATS.items(), key=lambda kv: kv[1]["files_sequenced"], reverse=True)[:5]

    if not top_users:
        await message.reply_text("No data available in the leaderboard yet!")
        return

    leaderboard_text = "**🏆 Top Users - File Sequencing 🏆**\n\n"
    for index, (uid, data) in enumerate(top_users, start=1):
        username = data.get('username', 'Unknown User')
        files_count = data.get('files_sequenced', 0)
        leaderboard_text += f"**{index}. {username}** - {files_count} files\n"

    await message.reply_text(leaderboard_text)
