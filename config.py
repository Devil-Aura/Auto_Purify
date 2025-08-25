import re, os, time
from os import environ, getenv
id_pattern = re.compile(r'^.\d+$') 


class Config(object):
    # Pyrogram client config
    API_ID    = os.environ.get("API_ID", "22768311")
    API_HASH  = os.environ.get("API_HASH", "702d8884f48b42e865425391432b3794")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "") 

    # Removed MongoDB config (not needed anymore)
    PORT = os.environ.get("PORT", "2340")
 
    # Other configs
    BOT_UPTIME  = time.time()
    START_PIC   = os.environ.get("START_PIC", "https://graph.org/file/255a7bf3992c1bfb4b78a-03d5d005ec6812a81d.jpg")
    ADMIN       = [int(admin) if id_pattern.search(admin) else admin for admin in os.environ.get('ADMIN', '5469101870').split()]
    FORCE_SUB_CHANNELS = os.environ.get('FORCE_SUB_CHANNELS', '@World_Fastest_Bots').split(',')
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1003058967184"))
    BOT_OWNER   = int(os.environ.get("BOT_OWNER", "6040503076"))
    DUMP_CHANNEL = int(os.environ.get("DUMP_CHANNEL", "-1003058967184"))
    
    # Webhook config     
    WEBHOOK = bool(os.environ.get("WEBHOOK", "True"))


class Txt(object):
    # Part of text configuration
        
    START_TXT = """<b>ʜᴇʏ! {}  

» I am an advanced Auto Rename Bot! I can rename your files with custom captions, thumbnails, and sequence them perfectly.</b>"""
    
    FILE_NAME_TXT = """<b>» <u>Setup auto rename format</u></b>

<b>Variables :</b>
➲ episode - replace with episode number  
➲ season  - replace with season number  
➲ quality - replace with quality  

<b>Example:</b> `/autorename Overflow [Sseason Eepisode] - [Dual] quality`"""

    ABOUT_TXT = f"""<b>❍ ᴍʏ ɴᴀᴍᴇ : <a href="https://t.me/World_Fastest_Bots">ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ</a>
❍ ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href="https://t.me/World_Fastest_Bots">World Fastest Bots</a>
❍ ʟᴀɴɢᴜᴀɢᴇ : <a href="https://www.python.org/">Python</a>
❍ ʜᴏꜱᴛᴇᴅ ᴏɴ : <a href="https://t.me/World_Fastest_Bots">Private Server</a>
❍ ᴍᴀɪɴ ᴄʜᴀɴɴᴇʟ : <a href="https://t.me/World_Fastest_Bots">World Fastest Bots</a></b>"""
    
    THUMBNAIL_TXT = """<b><u>» To set custom thumbnail</u></b>
    
➲ /start: Send any photo to automatically set as a thumbnail.
➲ /del_thumb: Delete your old thumbnail.
➲ /view_thumb: View your current thumbnail.

Note: If no thumbnail is saved, the original file thumbnail will be used."""
    
    CAPTION_TXT = """<b><u>» To set custom caption and media type</u></b>
    
<b>Variables :</b>         
size: {filesize}
duration: {duration}
filename: {filename}

➲ /set_caption: Set a custom caption.
➲ /see_caption: View your custom caption.
➲ /del_caption: Delete your custom caption."""
    
    PROGRESS_BAR = """\n
<b>» Size</b> : {1} | {2}
<b>» Done</b> : {0}%
<b>» Speed</b> : {3}/s
<b>» ETA</b> : {4} """
    
    DONATE_TXT = """<b>🙏 Thanks for showing interest in donations.</b>

Currently donations are not available.  
Stay tuned on @World_Fastest_Bots for updates!"""

    PREMIUM_TXT = """<b>Premium service is disabled in this bot build.</b>"""

    PREPLANS_TXT = """<b>No premium plans available.</b>"""
    
    HELP_TXT = """<b>📖 Help Menu

Awesome Features:
➲ /autorename - Auto rename your files
➲ /metadata - Manage metadata
➲ /help - Quick assistance</b>"""

    SOURCE_TXT = """<b>This bot is maintained by @World_Fastest_Bots</b>"""

    META_TXT = """<b>Metadata management is simplified in this build.</b>"""

    SEQUENCE_TXT = """<b>📦 Sequence Manager</b>

Commands:
➲ /startsequence - Start sequence
➲ /showsequence - Show collected files
➲ /endsequence - Process sequence
➲ /cancelsequence - Cancel sequence"""
