from config import Config, Txt
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
import os, sys, time, asyncio, logging, datetime
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ADMIN_USER_ID = Config.ADMIN

# Flag to indicate if the bot is restarting
is_restarting = False


# 🔄 Restart Command
@Client.on_message(filters.private & filters.command("restart") & filters.user(ADMIN_USER_ID))
async def restart_bot(b, m):
    global is_restarting
    if not is_restarting:
        is_restarting = True
        await m.reply_text("**Restarting.....**")

        # Gracefully stop the bot's event loop
        b.stop()
        time.sleep(2)  # Adjust delay duration if needed

        # Restart the bot process
        os.execl(sys.executable, sys.executable, *sys.argv)


# 📖 Tutorial Command
@Client.on_message(filters.private & filters.command("tutorial"))
async def tutorial(bot: Client, message: Message):
    await message.reply_text(
        text=Txt.FILE_NAME_TXT,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴄʜᴀɴɴᴇʟ", url="https://t.me/World_Fastest_Bots"),
             InlineKeyboardButton("• ᴏᴡɴᴇʀ", url="https://t.me/World_Fastest_Bots")]
        ])
    )


# 📊 Bot Status Command
@Client.on_message(filters.command(["stats", "status"]) & filters.user(Config.ADMIN))
async def get_stats(bot, message):
    uptime = time.strftime("%Hh%Mm%Ss", time.gmtime(time.time() - bot.uptime))
    start_t = time.time()
    st = await message.reply('**Accessing The Details.....**')
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000

    await st.edit(
        text=(
            f"**-- Bot Status --**\n\n"
            f"⏱ **Uptime :** {uptime}\n"
            f"📡 **Ping :** `{time_taken_s:.3f} ms`\n"
            f"⚡ **Powered by @World_Fastest_Bots**"
        )
    )


# 📢 Broadcast Command
@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN) & filters.reply)
async def broadcast_handler(bot: Client, m: Message):
    broadcast_msg = m.reply_to_message
    sts_msg = await m.reply_text("📢 Broadcast Started..!") 
    done = 0
    failed = 0
    success = 0
    start_time = time.time()

    # ⚡ Example static users list
    # You can update this list dynamically if needed
    all_users = Config.USERS  

    for user_id in all_users:
        sts = await send_msg(user_id, broadcast_msg)
        if sts == 200:
            success += 1
        else:
            failed += 1
        done += 1
        if not done % 20:
            await sts_msg.edit(
                f"📢 Broadcast In Progress:\n\n"
                f"✅ Success : {success}\n"
                f"❌ Failed : {failed}\n"
                f"👥 Completed : {done}/{len(all_users)}"
            )

    completed_in = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts_msg.edit(
        f"🎉 **Broadcast Completed** 🎉\n\n"
        f"⏱ Time Taken: `{completed_in}`\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total: {len(all_users)}\n\n"
        f"⚡ Powered by @World_Fastest_Bots"
    )


# 📨 Broadcast Helper
async def send_msg(user_id, message):
    try:
        await message.copy(chat_id=int(user_id))
        return 200
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_msg(user_id, message)
    except InputUserDeactivated:
        logger.info(f"{user_id} : Deactivated")
        return 400
    except UserIsBlocked:
        logger.info(f"{user_id} : Blocked The Bot")
        return 400
    except PeerIdInvalid:
        logger.info(f"{user_id} : User ID Invalid")
        return 400
    except Exception as e:
        logger.error(f"{user_id} : {e}")
        return 500
