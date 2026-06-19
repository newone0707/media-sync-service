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
            [InlineKeyboardButton("🎓 Ganitank/Spayee", callback_data="platform_spayee")],
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
        
    elif data == "platform_spayee":
        set_state(user_id, "WAITING_FOR_SPAYEE_CREDS")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="menu_platforms")]
        ])
        await query.message.edit_caption(
            caption=(
                "**🎓 Ganitank / Spayee Extraction Engine**\n\n"
                "Please send your Spayee API URL and Credentials in the chat.\n\n"
                "**Format:**\n"
                "`[API_URL] [EMAIL]*[PASSWORD]`\n\n"
                "> _Example:_\n"
                "> `https://www.ganitank.com myemail@gmail.com*mypassword`"
            ),
            reply_markup=keyboard
        )
        
    elif data == "platform_soon":
        await query.answer("This platform will be added in a future update!", show_alert=True)
        
    elif data.startswith("spcourse_"):
        course_id = data.split("_")[1]
        user_id = query.from_user.id
        from plugins.uploader import spayee_clients
        if "spayee_clients" not in globals() and 'spayee_clients' not in locals() and user_id not in getattr(sys.modules.get('plugins.uploader', object()), 'spayee_clients', {}):
            try:
                from plugins.uploader import spayee_clients
            except:
                spayee_clients = {}
                
        if user_id not in spayee_clients:
            await query.answer("Session expired! Please login again.", show_alert=True)
            return
            
        spayee_client = spayee_clients[user_id]
        await query.message.edit_text("⏳ **Extracting course safely (this may take a few minutes)...**")
        
        import asyncio
        import os
        async def extract_task():
            try:
                links = await spayee_client.extract_links(course_id)
                if not links:
                    await query.message.edit_text("❌ **No links found in this course.**")
                    return
                
                # Write to text file
                file_name = f"Ganitank_{course_id}.txt"
                with open(file_name, "w", encoding="utf-8") as f:
                    f.write(f"BaseURL: {spayee_client.domain_url}\n\n")
                    f.write("\n".join(links))
                
                await query.message.reply_document(
                    document=file_name,
                    caption=f"✅ **Extraction Complete!**\nFound {len(links)} links.\n\n_Forward this file back to me to start downloading!_"
                )
                os.remove(file_name)
            except Exception as e:
                await query.message.edit_text(f"❌ **Extraction Error:**\n`{str(e)}`")
                
        asyncio.create_task(extract_task())
