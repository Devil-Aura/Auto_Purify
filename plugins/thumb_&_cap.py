from pyrogram import Client, filters

# Temporary in-memory storage (resets on restart)
captions = {}
thumbnails = {}


# 📝 Set Caption
@Client.on_message(filters.private & filters.command('set_caption'))
async def add_caption(client, message):
    if len(message.command) == 1:
        return await message.reply_text(
            "**Give The Caption\n\nExample :-**\n"
            "`/set_caption 📕Name ➠ : {filename}\n\n🔗 Size ➠ : {filesize}\n\n⏰ Duration ➠ : {duration}`"
        )
    caption = message.text.split(" ", 1)[1]
    captions[message.from_user.id] = caption
    await message.reply_text("**Your Caption Successfully Added ✅**")


# 🗑️ Delete Caption
@Client.on_message(filters.private & filters.command('del_caption'))
async def delete_caption(client, message):
    if message.from_user.id not in captions:
        return await message.reply_text("**You Don't Have Any Caption ❌**")
    captions.pop(message.from_user.id, None)
    await message.reply_text("**Your Caption Successfully Deleted 🗑️**")


# 👀 View Caption
@Client.on_message(filters.private & filters.command(['see_caption', 'view_caption']))
async def see_caption(client, message):
    caption = captions.get(message.from_user.id)
    if caption:
        await message.reply_text(f"**Your Caption :**\n\n`{caption}`")
    else:
        await message.reply_text("**You Don't Have Any Caption ❌**")


# 👀 View Thumbnail
@Client.on_message(filters.private & filters.command(['view_thumb', 'viewthumb']))
async def viewthumb(client, message):    
    thumb = thumbnails.get(message.from_user.id)
    if thumb:
        await client.send_photo(chat_id=message.chat.id, photo=thumb)
    else:
        await message.reply_text("**You Don't Have Any Thumbnail ❌**") 


# 🗑️ Delete Thumbnail
@Client.on_message(filters.private & filters.command(['del_thumb', 'delthumb']))
async def removethumb(client, message):
    if message.from_user.id in thumbnails:
        thumbnails.pop(message.from_user.id, None)
        await message.reply_text("**Thumbnail Deleted Successfully 🗑️**")
    else:
        await message.reply_text("**You Don't Have Any Thumbnail ❌**")


# 📸 Save Thumbnail
@Client.on_message(filters.private & filters.photo)
async def addthumbs(client, message):
    mkn = await message.reply_text("Please Wait ...")
    thumbnails[message.from_user.id] = message.photo.file_id
    await mkn.edit("**Thumbnail Saved Successfully ✅️**")
