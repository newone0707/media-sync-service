from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot_state import set_state, clear_state

@Client.on_callback_query()
async def handle_callbacks(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    if data == "menu_main":
        clear_state(user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Login & Extract", callback_data="menu_platforms")],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
                InlineKeyboardButton("❓ Help", callback_data="menu_help")
            ]
        ])
        await query.message.edit_caption(
            caption=(
                "**⚡ WELCOME TO CLEAN LEACH ENGINE ⚡**\n\n"
                "> _Your ultimate automated extraction and uploading suite._\n\n"
                "💠 **Status:** `Online & Ready`\n"
                "💠 **WAF Bypass:** `Active`\n\n"
                "**Select an option below to begin your extraction:**"
            ),
            reply_markup=keyboard
        )
        
    elif data == "menu_platforms":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 AppX", callback_data="platform_appx")],
            [InlineKeyboardButton("📚 Classplus", callback_data="platform_classplus")],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]
        ])
        await query.message.edit_caption(
            caption=(
                "**Select a Platform:**\n\n"
                "> _Choose the API engine you want to use._"
            ),
            reply_markup=keyboard
        )
        
    elif data == "platform_appx":
        set_state(user_id, "WAITING_FOR_APPX_CREDS")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="menu_platforms")]
        ])
        await query.message.edit_caption(
            caption=(
                "**📱 AppX Extraction Engine**\n\n"
                "Please send your target API URL and your Credentials (or JWT Token) in the chat.\n\n"
                "**Format:**\n"
                "`[API_URL] [EMAIL]*[PASSWORD]`\n"
                "**OR**\n"
                "`[API_URL] [JWT_TOKEN]`\n\n"
                "> _Example:_\n"
                "> `https://api.example.com user@mail.com*pass123`"
            ),
            reply_markup=keyboard
        )
        
    elif data == "menu_settings":
        await query.answer("Settings coming soon!", show_alert=True)
        
    elif data == "menu_help":
        await query.answer("Help coming soon!", show_alert=True)
        
    elif data == "platform_classplus":
        set_state(user_id, "WAITING_FOR_CLASSPLUS_PHONE")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="menu_platforms")]
        ])
        await query.message.edit_caption(
            caption=(
                "**📚 Classplus Extraction Engine**\n\n"
                "Please send your `orgCode` and your `Mobile Number` in the chat to generate an OTP. \n"
                "*(You can also directly send a JWT Token to bypass OTP)*\n\n"
                "**Format:**\n"
                "`[ORG_CODE]*[MOBILE_NUMBER]` \n"
                "**OR**\n"
                "`eyJhbGciOiJIUzI1NiIsInR5...`\n\n"
                "> _Example:_\n"
                "> `aiex*9999999999`"
            ),
            reply_markup=keyboard
        )
        
    elif data == "platform_soon":
        await query.answer("This platform will be added in a future update!", show_alert=True)
