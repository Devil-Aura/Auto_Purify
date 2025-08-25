from helper.database import codeflixbots as db
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import Txt


# 📌 /metadata command
@Client.on_message(filters.command("metadata"))
async def metadata(client, message):
    user_id = message.from_user.id

    # Fetch user metadata from the database
    current = await db.get_metadata(user_id)
    title = await db.get_title(user_id)
    author = await db.get_author(user_id)
    artist = await db.get_artist(user_id)
    video = await db.get_video(user_id)
    audio = await db.get_audio(user_id)
    subtitle = await db.get_subtitle(user_id)

    # Display the current metadata
    text = f"""
**㊋ Yᴏᴜʀ Mᴇᴛᴀᴅᴀᴛᴀ ɪꜱ ᴄᴜʀʀᴇɴᴛʟʏ: {current}**

**◈ Tɪᴛʟᴇ ▹** `{title or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
**◈ Aᴜᴛʜᴏʀ ▹** `{author or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
**◈ Aʀᴛɪꜱᴛ ▹** `{artist or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
**◈ Aᴜᴅɪᴏ ▹** `{audio or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
**◈ Sᴜʙᴛɪᴛʟᴇ ▹** `{subtitle or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
**◈ Vɪᴅᴇᴏ ▹** `{video or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
    """

    # Inline buttons
    buttons = [
        [
            InlineKeyboardButton(f"On{' ✅' if current == 'On' else ''}", callback_data='on_metadata'),
            InlineKeyboardButton(f"Off{' ✅' if current == 'Off' else ''}", callback_data='off_metadata')
        ],
        [InlineKeyboardButton("ℹ How to Set Metadata", callback_data="metainfo")]
    ]

    await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


# 📌 Metadata toggle & info callback
@Client.on_callback_query(filters.regex(r"on_metadata|off_metadata|metainfo"))
async def metadata_callback(client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data

    if data == "on_metadata":
        await db.set_metadata(user_id, "On")
    elif data == "off_metadata":
        await db.set_metadata(user_id, "Off")
    elif data == "metainfo":
        await query.message.edit_text(
            text=Txt.META_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Home", callback_data="home"),
                 InlineKeyboardButton("❌ Close", callback_data="close")]
            ])
        )
        return

    # Fetch updated metadata
    current = await db.get_metadata(user_id)
    title = await db.get_title(user_id)
    author = await db.get_author(user_id)
    artist = await db.get_artist(user_id)
    video = await db.get_video(user_id)
    audio = await db.get_audio(user_id)
    subtitle = await db.get_subtitle(user_id)

    text = f"""
**㊋ Yᴏᴜʀ Mᴇᴛᴀᴅᴀᴛᴀ ɪꜱ ᴄᴜʀʀᴇɴᴛʟʏ: {current}**

**◈ Tɪᴛʟᴇ ▹** `{title or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
**◈ Aᴜᴛʜᴏʀ ▹** `{author or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
**◈ Aʀᴛɪꜱᴛ ▹** `{artist or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
**◈ Aᴜᴅɪᴏ ▹** `{audio or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
**◈ Sᴜʙᴛɪᴛʟᴇ ▹** `{subtitle or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
**◈ Vɪᴅᴇᴏ ▹** `{video or 'Nᴏᴛ ꜰᴏᴜɴᴅ'}`  
    """

    buttons = [
        [
            InlineKeyboardButton(f"On{' ✅' if current == 'On' else ''}", callback_data='on_metadata'),
            InlineKeyboardButton(f"Off{' ✅' if current == 'Off' else ''}", callback_data='off_metadata')
        ],
        [InlineKeyboardButton("ℹ How to Set Metadata", callback_data="metainfo")]
    ]
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


# 📌 Metadata Setters
@Client.on_message(filters.private & filters.command('settitle'))
async def set_title_cmd(client, message):
    if len(message.command) == 1:
        return await message.reply_text("**Usage:** `/settitle Encoded By @World_Fastest_Bots`")
    title = message.text.split(" ", 1)[1]
    await db.set_title(message.from_user.id, title=title)
    await message.reply_text("✅ Title Saved")


@Client.on_message(filters.private & filters.command('setauthor'))
async def set_author_cmd(client, message):
    if len(message.command) == 1:
        return await message.reply_text("**Usage:** `/setauthor @World_Fastest_Bots`")
    author = message.text.split(" ", 1)[1]
    await db.set_author(message.from_user.id, author=author)
    await message.reply_text("✅ Author Saved")


@Client.on_message(filters.private & filters.command('setartist'))
async def set_artist_cmd(client, message):
    if len(message.command) == 1:
        return await message.reply_text("**Usage:** `/setartist @World_Fastest_Bots`")
    artist = message.text.split(" ", 1)[1]
    await db.set_artist(message.from_user.id, artist=artist)
    await message.reply_text("✅ Artist Saved")


@Client.on_message(filters.private & filters.command('setaudio'))
async def set_audio_cmd(client, message):
    if len(message.command) == 1:
        return await message.reply_text("**Usage:** `/setaudio @World_Fastest_Bots`")
    audio = message.text.split(" ", 1)[1]
    await db.set_audio(message.from_user.id, audio=audio)
    await message.reply_text("✅ Audio Saved")


@Client.on_message(filters.private & filters.command('setsubtitle'))
async def set_subtitle_cmd(client, message):
    if len(message.command) == 1:
        return await message.reply_text("**Usage:** `/setsubtitle Subtitles by @World_Fastest_Bots`")
    subtitle = message.text.split(" ", 1)[1]
    await db.set_subtitle(message.from_user.id, subtitle=subtitle)
    await message.reply_text("✅ Subtitle Saved")


@Client.on_message(filters.private & filters.command('setvideo'))
async def set_video_cmd(client, message):
    if len(message.command) == 1:
        return await message.reply_text("**Usage:** `/setvideo Encoded by @World_Fastest_Bots`")
    video = message.text.split(" ", 1)[1]
    await db.set_video(message.from_user.id, video=video)
    await message.reply_text("✅ Video Saved")
