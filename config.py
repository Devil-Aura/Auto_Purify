import re, os, time

id_pattern = re.compile(r'^.\d+$')

class Config(object):
    # Pyrogram client config
    API_ID    = os.environ.get("API_ID", "22768311")
    API_HASH  = os.environ.get("API_HASH", "702d8884f48b42e865425391432b3794")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

    # Removed MongoDB completely
    PORT = os.environ.get("PORT", "2340")

    # Other configs
    BOT_UPTIME  = time.time()
    START_PIC   = os.environ.get("START_PIC", "https://graph.org/file/255a7bf3992c1bfb4b78a-03d5d005ec6812a81d.jpg")
    ADMIN       = [int(a) if id_pattern.search(a) else a for a in os.environ.get('ADMIN', '5469101870').split()] if os.environ.get('ADMIN') else []
    FORCE_SUB_CHANNELS = os.environ.get('FORCE_SUB_CHANNELS', '@World_Fastest_Bots').split(',')
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1003058967184"))
    BOT_OWNER   = int(os.environ.get("BOT_OWNER", "6040503076"))
    DUMP_CHANNEL = int(os.environ.get("DUMP_CHANNEL", "-1003058967184"))

    # Webhook toggle (not used in this minimal run)
    WEBHOOK = bool(os.environ.get("WEBHOOK", "True"))

class Txt(object):
    START_TXT = """<b>ʜᴇʏ! {}

» I am an advanced Auto Rename Bot! I can auto-rename your files with custom captions, thumbnails and sequence them perfectly.</b>"""

    FILE_NAME_TXT = """<b>» <u>Setup auto rename format</u></b>

<b>Variables :</b>
• <code>{episode}</code> – episode number
• <code>{season}</code> – season number
• <code>{quality}</code> – quality (e.g. 1080p)

<b>Example:</b> <code>/autorename Overflow [S{season} E{episode}] - [Dual] {quality}</code>"""

    ABOUT_TXT = """<b>❍ ᴍʏ ɴᴀᴍᴇ : <a href="https://t.me/World_Fastest_Bots">Auto Rename</a>
❍ ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href="https://t.me/World_Fastest_Bots">World Fastest Bots</a>
❍ ʟᴀɴɢᴜᴀɢᴇ : <a href="https://www.python.org/">Python</a>
❍ ʜᴏꜱᴛᴇᴅ ᴏɴ : Private Server
❍ ᴍᴀɪɴ ᴄʜᴀɴɴᴇʟ : <a href="https://t.me/World_Fastest_Bots">World Fastest Bots</a></b>"""

    THUMBNAIL_TXT = """<b><u>» Custom thumbnail</u></b>
• Send a photo while in /start to set as thumbnail
• /del_thumb – delete thumbnail
• /view_thumb – view thumbnail

If no thumbnail is saved, file's original thumb is used."""

    CAPTION_TXT = """<b><u>» Custom caption</u></b>

<b>Variables:</b>
• <code>{filename}</code> • <code>{filesize}</code> • <code>{duration}</code>

• /set_caption – set a custom caption
• /see_caption – view your caption
• /del_caption – delete your caption"""

    PROGRESS_BAR = """\n<b>» Done</b> : {0}%\n<b>» Size</b> : {1} | {2}\n<b>» Speed</b> : {3}/s\n<b>» ETA</b> : {4}"""

    DONATE_TXT = "<b>Donations are not available right now. Follow @World_Fastest_Bots for updates.</b>"
    PREMIUM_TXT = "<b>Premium features are disabled in this build.</b>"
    PREPLANS_TXT = "<b>No premium plans available.</b>"

    HELP_TXT = """<b>📖 Help</b>

• /autorename – set template for auto-rename
• /metadata – manage metadata (title/author/artist/audio/subtitle/video)
• /help – show this help"""

    SOURCE_TXT = "<b>This bot is maintained by @World_Fastest_Bots</b>"
    META_TXT = "<b>Use /metadata to toggle & set fields using /settitle /setauthor /setartist /setaudio /setsubtitle /setvideo</b>"

    SEQUENCE_TXT = """<b>📦 Sequence Manager</b>
• /startsequence – start
• /showsequence – list
• /endsequence – finish & send in order
• /cancelsequence – cancel"""
