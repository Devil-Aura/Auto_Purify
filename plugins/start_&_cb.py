import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from helper.storage import codeflixbots  # changed
from config import *
from config import Config
from config import Txt

# Start Command Handler
@Client.on_message(filters.private & filters.command("start"))
async def start(client, message: Message):
    user = message.from_user
    await codeflixbots.add_user(client, message)

    m = await message.reply_text("☎️")
    await asyncio.sleep(0.5)
    await m.edit_text("<code>Dᴇᴠɪʟ ᴍᴀʏ ᴄʀʏ...</code>")
    await asyncio.sleep(0.4)
    await m.edit_text("⚡")
    await asyncio.sleep(0.5)
    await m.edit_text("<code>Jᴀᴄᴋᴘᴏᴛ!!!</code>")
    await asyncio.sleep(0.4)
    await m.delete()

    await message.reply_sticker("CAACAgQAAxkBAAIOsGf5RIq9Zodm25_NfFJGKNFNFJv5AALHGAACukfIUwkk20UPuRnvNgQ")

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs •", callback_data='help')],
        [InlineKeyboardButton("• ᴘʀᴇᴍɪᴜᴍ •", callback_data='premiumx')],
        [InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇs', url='https://t.me/+ecWFJBaAGZpjMGY1'),
         InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ •', url='https://t.me/weebs_talk_station')],
        [InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about')]
    ])

    if Config.START_PIC:
        await message.reply_photo(
            Config.START_PIC,
            caption=Txt.START_TXT.format(user.mention),
            reply_markup=buttons
        )
    else:
        await message.reply_text(
            text=Txt.START_TXT.format(user.mention),
            reply_markup=buttons,
            disable_web_page_preview=True
        )

@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    print(f"Callback data received: {data}")

    if data == "home":
        await query.message.edit_text(
            text=Txt.START_TXT.format(query.from_user.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs •", callback_data='help')],
                [InlineKeyboardButton("• ᴘʀᴇᴍɪᴜᴍ •", callback_data='premiumx')],
                [InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇs', url='https://t.me/AS_Networks'),
                 InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ •', url='https://t.me/weebs_talk_station')],
                [InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about'),
                 InlineKeyboardButton('sᴏᴜʀᴄᴇ •', callback_data='source')]
            ])
        )
    elif data == "caption":
        await query.message.edit_text(
            text=Txt.CAPTION_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• sᴜᴘᴘᴏʀᴛ", url='https://t.me/weebs_talk_station'),
                 InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )

    elif data == "help":
        format_template = await codeflixbots.get_format_template(user_id)
        await query.message.edit_text(
            text=Txt.HELP_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ •", callback_data='file_names')],
                [InlineKeyboardButton("• sᴇǫᴜᴇɴᴄᴇ ғɪʟᴇs •", callback_data='sequence_help')],
                [InlineKeyboardButton('• ᴛʜᴜᴍʙɴᴀɪʟ', callback_data='thumbnail'),
                 InlineKeyboardButton('ᴄᴀᴘᴛɪᴏɴ •', callback_data='caption')],
                [InlineKeyboardButton('• ᴍᴇᴛᴀᴅᴀᴛᴀ', callback_data='meta'),
                 InlineKeyboardButton('ᴅᴏɴᴀᴛᴇ •', callback_data='donate')],
                [InlineKeyboardButton('• ʜᴏᴍᴇ', callback_data='home')]
            ])
        )

    elif data == "meta":
        await query.message.edit_text(
            text=Txt.SEND_METADATA,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                 InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "donate":
        await query.message.edit_text(
            text=Txt.DONATE_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="help"),
                 InlineKeyboardButton("ᴏᴡɴᴇʀ •", url='https://t.me/IntrovertSama')]
            ])
        )
    elif data == "file_names":
        format_template = await codeflixbots.get_format_template(user_id)
        await query.message.edit_text(
            text=Txt.FILE_NAME_TXT.format(format_template=format_template),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                 InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "thumbnail":
        await query.message.edit_caption(
            caption=Txt.THUMBNAIL_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                 InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "sequence_help":
        await query.message.edit_caption(
            caption=Txt.SEQUENCE_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                 InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "metadatax":
        await query.message.edit_caption(
            caption=Txt.SEND_METADATA,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                 InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "source":
        await query.message.edit_caption(
            caption=Txt.SOURCE_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                 InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="home")]
            ])
        )
    elif data == "premiumx":
        await query.message.edit_caption(
            caption=Txt.PREMIUM_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴘʟᴀɴs •", callback_data='plans')],
                [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="help"),
                 InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url='https://t.me/IntrovertSama')]
            ])
        )
    elif data == "plans":
        await query.message.edit_caption(
            caption=Txt.PREPLANS_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                 InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url='https://t.me/introvertsama')]
            ])
        )
    elif data == "about":
        await query.message.edit_text(
            text=Txt.ABOUT_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• sᴜᴘᴘᴏʀᴛ", url='https://t.me/weebs_talk_station'),
                 InlineKeyboardButton("ᴄᴏᴍᴍᴀɴᴅs •", callback_data="help")],
                [InlineKeyboardButton("• ᴅᴇᴠᴇʟᴏᴘᴇʀ", url='https://t.me/IntrovertSama'),
                 InlineKeyboardButton("ɴᴇᴛᴡᴏʀᴋ •", url='https://t.me/AS_Networks')],
                [InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="home")]
            ])
        )
    elif data == "close":
        try:
            await query.message.delete()
            await query.message.reply_to_message.delete()
            await query.message.continue_propagation()
        except:
            await query.message.delete()
            await query.message.continue_propagation()

@Client.on_message(filters.command("donate"))
async def donation(client, message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="ʙᴀᴄᴋ", callback_data="help"),
         InlineKeyboardButton(text="ᴏᴡɴᴇʀ", url='https://t.me/sewxiy')]
    ])
    yt = await message.reply_photo(photo='https://i.ibb.co/S7vgk8Hj/c8d9f3039813.jpg', caption=Txt.DONATE_TXT, reply_markup=buttons)
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

@Client.on_message(filters.command("premium"))
async def getpremium(bot, message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("• ᴘʟᴀɴs •", callback_data='plans')],
        [InlineKeyboardButton("ᴏᴡɴᴇʀ", url="https://t.me/IntrovertSama"),
         InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]
    ])
    yt = await message.reply_photo(photo='https://i.ibb.co/S7vgk8Hj/c8d9f3039813.jpg', caption=Txt.PREMIUM_TXT, reply_markup=buttons)
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

@Client.on_message(filters.command("plan"))
async def premium(bot, message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("sᴇɴᴅ ss", url="https://t.me/IntrovertSama"),
         InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]
    ])
    yt = await message.reply_photo(photo='https://i.ibb.co/S7vgk8Hj/c8d9f3039813.jpg', caption=Txt.PREPLANS_TXT, reply_markup=buttons)
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

@Client.on_message(filters.command("bought") & filters.private)
async def bought(client, message):
    msg = await message.reply('Wait im checking...')
    replied = message.reply_to_message

    if not replied:
        await msg.edit("<b>Please reply with the screenshot of your payment for the premium purchase to proceed.\n\nFor example, first upload your screenshot, then reply to it using the '/bought' command</b>")
    elif replied.photo:
        await client.send_photo(
            chat_id=Config.LOG_CHANNEL,
            photo=replied.photo.file_id,
            caption=f'<b>User - {message.from_user.mention}\nUser id - <code>{message.from_user.id}</code>\nUsername - <code>{message.from_user.username}</code>\nName - <code>{message.from_user.first_name}</code></b>',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close_data")]])
        )
        await msg.edit_text('<b>Your screenshot has been sent to Admins</b>')

@Client.on_message(filters.private & filters.command("help"))
async def help_command(client, message):
    await message.reply_text(
        text=Txt.HELP_TXT,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ •", callback_data='file_names')],
            [InlineKeyboardButton("• sᴇǫᴜᴇɴᴄᴇ ғɪʟᴇs •", callback_data='sequence_help')],
            [InlineKeyboardButton('• ᴛʜᴜᴍʙɴᴀɪʟ', callback_data='thumbnail'),
             InlineKeyboardButton('ᴄᴀᴘᴛɪᴏɴ •', callback_data='caption')],
            [InlineKeyboardButton('• ᴍᴇᴛᴀᴅᴀᴛᴀ', callback_data='meta'),
             InlineKeyboardButton('ᴅᴏɴᴀᴛᴇ •', callback_data='donate')],
            [InlineKeyboardButton('• ʜᴏᴍᴇ', callback_data='home')]
        ])
        )
