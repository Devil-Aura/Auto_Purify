import math, time, re
from datetime import datetime
from pytz import timezone
from config import Config, Txt
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


async def progress_for_pyrogram(current, total, ud_type, message, start):
    """
    Safe progress callback for Pyrogram downloads/uploads.
    Shows ■/□ progress bar with percent, speed, eta.
    """
    now = time.time()
    diff = max(now - start, 1e-6)  # avoid division by zero
    if current == total or round(diff % 5.00) == 0:
        percentage = 0 if not total else (current * 100 / total)
        speed = current / diff if diff else 0

        elapsed_time_ms = int(diff * 1000)
        time_to_completion_ms = 0 if speed == 0 or not total else int(((total - current) / speed) * 1000)
        estimated_total_time_ms = elapsed_time_ms + time_to_completion_ms

        eta_str = TimeFormatter(milliseconds=estimated_total_time_ms) if estimated_total_time_ms > 0 else "0 s"

        # Progress bar
        filled = "■" * int(math.floor(percentage / 5))
        empty  = "□" * (20 - int(math.floor(percentage / 5)))
        progress = f"{filled}{empty}"

        tmp = progress + Txt.PROGRESS_BAR.format(
            round(percentage, 2),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            eta_str
        )
        try:
            await message.edit(
                text=f"{ud_type}\n\n{tmp}",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("• ᴄᴀɴᴄᴇʟ •", callback_data="close")]]
                )
            )
        except Exception:
            pass  # ignore if message deleted


def humanbytes(size):
    """Human readable bytes (K/M/G/T) + ʙ."""
    if not size:
        return "0 ʙ"
    power = 2 ** 10
    n = 0
    units = ["", "K", "M", "G", "T", "P"]
    size = float(size)
    while size >= power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{round(size, 2)} {units[n]}ʙ"


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "ᴅ, ") if days else "") + \
          ((str(hours) + "ʜ, ") if hours else "") + \
          ((str(minutes) + "ᴍ, ") if minutes else "") + \
          ((str(seconds) + "ꜱ, ") if seconds else "") + \
          ((str(milliseconds) + "ᴍꜱ, ") if milliseconds else "")
    return tmp[:-2]


def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hour, minutes, seconds)


async def send_log(b, u):
    """
    Logs a new user start to LOG_CHANNEL with @World_Fastest_Bots mention.
    """
    if Config.LOG_CHANNEL is not None:
        curr = datetime.now(timezone("Asia/Kolkata"))
        date = curr.strftime('%d %B, %Y')
        time_str = curr.strftime('%I:%M:%S %p')

        try:
            me = await b.get_me()
            by_text = f"@{me.username}" if getattr(me, "username", None) else "@World_Fastest_Bots"
        except Exception:
            by_text = "@World_Fastest_Bots"

        uname = f"@{u.username}" if getattr(u, "username", None) else "N/A"

        await b.send_message(
            Config.LOG_CHANNEL,
            f"**--Nᴇᴡ Uꜱᴇʀ Sᴛᴀʀᴛᴇᴅ Tʜᴇ Bᴏᴛ--**\n\n"
            f"Uꜱᴇʀ: {u.mention}\n"
            f"Iᴅ: `{u.id}`\n"
            f"Uɴ: {uname}\n\n"
            f"Dᴀᴛᴇ: {date}\n"
            f"Tɪᴍᴇ: {time_str}\n\n"
            f"By: {by_text}"
        )


def add_prefix_suffix(input_string, prefix='', suffix=''):
    """
    Adds optional prefix/suffix around base filename (keeps extension).
    """
    pattern = r'(?P<filename>.*?)(\.[^.]+)?$'
    match = re.search(pattern, input_string or "")
    if not match:
        return input_string

    filename = match.group('filename') or ""
    extension = match.group(2) or ""

    pre = "" if prefix in (None, "") else f"{prefix}"
    suf = "" if suffix in (None, "") else f" {suffix}"

    return f"{pre}{filename}{suf}{extension}"
