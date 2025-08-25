import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import UserNotParticipant

# Force subscribe channel
FORCE_SUB_CHANNEL = "World_Fastest_Bots"
CHANNEL_LINK = "https://t.me/World_Fastest_Bots"
IMAGE_URL = "https://i.ibb.co/gFQFknCN/d8a33273f73c.jpg"


async def not_subscribed(_, __, message):
    try:
        user = await message._client.get_chat_member(FORCE_SUB_CHANNEL, message.from_user.id)
        if user.status in {"kicked", "left"}:
            return True
    except UserNotParticipant:
        return True
    return False


@Client.on_message(filters.private & filters.create(not_subscribed))
async def forces_sub(client, message):
    buttons = [
        [InlineKeyboardButton("• ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ •", url=CHANNEL_LINK)],
        [InlineKeyboardButton("• ᴊᴏɪɴᴇᴅ •", callback_data="check_subscription")]
    ]

    text = "**ʙᴀᴋᴋᴀ!!, ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴊᴏɪɴᴇᴅ ᴛᴏ ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟ, ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ.**"
    await message.reply_photo(
        photo=IMAGE_URL,
        caption=text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_callback_query(filters.regex("check_subscription"))
async def check_subscription(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    try:
        user = await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        if user.status not in {"kicked", "left"}:
            new_text = "**✅ ʏᴏᴜ ʜᴀᴠᴇ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ. ɴᴏᴡ ᴜꜱᴇ /start 🔥**"
            await callback_query.message.edit_caption(
                caption=new_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("• ᴄʟɪᴄᴋ ʜᴇʀᴇ •", callback_data='help')]
                ])
            )
            return
    except UserNotParticipant:
        pass

    # Still not joined
    text = "**⚠️ ʏᴏᴜ ʜᴀᴠᴇ ɴᴏᴛ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟ. ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ.**"
    await callback_query.message.edit_caption(
        caption=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ •", url=CHANNEL_LINK)],
            [InlineKeyboardButton("• ᴊᴏɪɴᴇᴅ •", callback_data="check_subscription")]
        ])
    )
