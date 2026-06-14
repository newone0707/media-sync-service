from pyrogram import Client, filters
from pyrogram.types import Message
from config import OWNER_ID, AUTH_USERS

@Client.on_message(filters.command("addauth") & filters.user(OWNER_ID))
async def add_auth(client: Client, message: Message):
    try:
        new_user_id = int(message.command[1])
        if new_user_id in AUTH_USERS:
            await message.reply_text("⚠️ User is already authorized.")
        else:
            AUTH_USERS.append(new_user_id)
            await message.reply_text(f"✅ User `{new_user_id}` added successfully.")
            await client.send_message(new_user_id, "🎉 You have been granted access to the bot!")
    except (IndexError, ValueError):
        await message.reply_text("❌ Usage: `/addauth [user_id]`")

@Client.on_message(filters.command("rmauth") & filters.user(OWNER_ID))
async def rm_auth(client: Client, message: Message):
    try:
        user_id = int(message.command[1])
        if user_id == OWNER_ID:
            await message.reply_text("❌ You cannot remove the owner.")
            return
            
        if user_id in AUTH_USERS:
            AUTH_USERS.remove(user_id)
            await message.reply_text(f"✅ User `{user_id}` removed successfully.")
            await client.send_message(user_id, "❌ Your access to the bot has been revoked.")
        else:
            await message.reply_text("⚠️ User is not in the authorized list.")
    except (IndexError, ValueError):
        await message.reply_text("❌ Usage: `/rmauth [user_id]`")

@Client.on_message(filters.command("users") & filters.user(OWNER_ID))
async def list_users(client: Client, message: Message):
    user_list = "\n".join([f"`{uid}`" for uid in AUTH_USERS])
    await message.reply_text(f"**Authorized Users:**\n{user_list}")
