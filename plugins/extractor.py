import os
import time
from datetime import datetime
from pyrogram import Client, filters, ContinuePropagation
from pyrogram.types import Message
from extractors.api_client import AppxClient
from config import AUTH_USERS
from bot_state import get_state, clear_state

@Client.on_message(filters.text & filters.private & ~filters.command(["start", "help", "extract", "upload", "stop"]))
async def handle_text(client: Client, message: Message):
    user_id = message.from_user.id
    state = get_state(user_id)
    
    if state == "WAITING_FOR_APPX_CREDS":
        clear_state(user_id)
        # Inject a fake command to reuse the extraction logic
        message.text = f"/extract {message.text}"
        await extract_cmd(client, message)
        return
        
    if state == "WAITING_FOR_CLASSPLUS_PHONE":
        text = message.text.strip()
        
        # Token Bypass Logic
        if text.startswith("eyJ") and len(text) > 50:
            status_msg = await message.reply_text("⏳ **Verifying Token Bypass...**")
            from extractors.classplus_api import ClassplusClient
            cp = ClassplusClient(org_code="UNKNOWN")
            cp.token = text
            cp.headers["x-access-token"] = text
            
            courses_resp = cp.fetch_courses()
            if not courses_resp.get("success"):
                await status_msg.edit_text(f"❌ **Token Verification Failed:** {courses_resp.get('error')}")
                return
                
            clear_state(user_id)
            
            import base64
            import json
            try:
                payload = cp.token.split(".")[1]
                padded = payload + "=" * ((4 - len(payload) % 4) % 4)
                jwt_data = json.loads(base64.b64decode(padded).decode("utf-8"))
            except:
                jwt_data = {}
                
            org = jwt_data.get("orgCode", "UNKNOWN")
            name = jwt_data.get("name", "User")
            
            courses = courses_resp.get("data", {}).get("data", {}).get("courses", []) if "data" in courses_resp else []
            if not courses and isinstance(courses_resp.get("data"), dict):
                 courses = courses_resp.get("data").get("courses", [])
                 
            resp_text = f"**ClassPlus Login Successful ✅**\n\n"
            resp_text += f"**ORG :** `{org}`\n\n"
            resp_text += f"`{cp.token}`\n\n"
            resp_text += f"**BATCH ID ➤ BATCH NAME**\n\n"
            for c in courses:
                resp_text += f"`{c.get('id')}` - **{c.get('name')}**\n"
                
            resp_text += "\n**Reply to this message with the BATCH ID you want to extract.**"
            
            if not hasattr(client, "user_sessions"):
                client.user_sessions = {}
                
            client.user_sessions[message.from_user.id] = {
                "appx": cp,
                "courses": courses,
                "app_name": "CLASSPLUS",
                "base_url": cp.base_url
            }
            
            await status_msg.edit_text(resp_text)
            return
            
        parts = text.split("*")
        if len(parts) != 2:
            await message.reply_text("❌ Invalid format. Please send `[ORG_CODE]*[MOBILE_NUMBER]` or a valid `JWT Token`.")
            return
            
        org_code, mobile = parts[0].strip(), parts[1].strip()
        status_msg = await message.reply_text("⏳ **Requesting OTP...**")
        
        from extractors.classplus_api import ClassplusClient
        cp = ClassplusClient(org_code)
        resp = cp.generate_otp(mobile)
        
        if resp.get("status") == "success" or resp.get("data"):
            session_id = resp.get("data", {}).get("sessionId", "")
            set_state(user_id, f"WAITING_FOR_CLASSPLUS_OTP|{org_code}|{mobile}|{session_id}")
            await status_msg.edit_text("✅ **OTP Sent successfully!**\n\nPlease reply with the OTP you received:\n> _Example:_ `1234`")
        else:
            await status_msg.edit_text(f"❌ **Failed to send OTP:** {resp.get('message', 'Unknown error')}")
        return
        
    if str(state).startswith("WAITING_FOR_CLASSPLUS_OTP"):
        parts = state.split("|")
        if len(parts) < 3:
            return
        org_code = parts[1]
        mobile = parts[2]
        
        otp = message.text.strip()
        status_msg = await message.reply_text("⏳ **Verifying OTP...**")
        
        from extractors.classplus_api import ClassplusClient
        cp = ClassplusClient(org_code)
        resp = cp.verify_otp(mobile, otp)
        
        if not resp.get("success"):
            await status_msg.edit_text(f"❌ **OTP Verification Failed:** {resp.get('error')}")
            return
            
        clear_state(user_id)
        token = cp.token
        courses_resp = cp.fetch_courses()
        
        if not courses_resp.get("success"):
            await status_msg.edit_text("❌ **Logged in, but failed to fetch courses.**")
            return
            
        import base64
        import json
        try:
            payload = cp.token.split(".")[1]
            padded = payload + "=" * ((4 - len(payload) % 4) % 4)
            jwt_data = json.loads(base64.b64decode(padded).decode("utf-8"))
        except:
            jwt_data = {}
            
        org = jwt_data.get("orgCode", org_code)
        name = jwt_data.get("name", "User")
        
        courses = courses_resp.get("data", {}).get("data", {}).get("courses", []) if "data" in courses_resp else []
        if not courses and isinstance(courses_resp.get("data"), dict):
             courses = courses_resp.get("data").get("courses", [])
             
        resp_text = f"**ClassPlus Login Successful ✅**\n\n"
        resp_text += f"**ORG :** `{org}`\n\n"
        resp_text += f"`{cp.token}`\n\n"
        resp_text += f"**BATCH ID ➤ BATCH NAME**\n\n"
        for c in courses:
            resp_text += f"`{c.get('id')}` - **{c.get('name')}**\n"
            
        resp_text += "\n**Reply to this message with the BATCH ID you want to extract.**"
        
        if not hasattr(client, "user_sessions"):
            client.user_sessions = {}
            
        client.user_sessions[message.from_user.id] = {
            "appx": cp,
            "courses": courses,
            "app_name": "CLASSPLUS",
            "base_url": cp.base_url
        }
        
        await status_msg.edit_text(resp_text)
        return

    raise ContinuePropagation

@Client.on_message(filters.command("extract") & filters.private)
async def extract_cmd(client: Client, message: Message):
    # if message.from_user.id not in AUTH_USERS:
    #     return

    try:
        parts = message.text.split(" ")
        if len(parts) != 3:
            raise ValueError()
        base_url = parts[1]
        creds = parts[2]
        
        is_token = False
        if "*" in creds:
            email, password = creds.split("*", 1)
        elif ":" in creds:
            email, password = creds.split(":", 1)
        elif creds.startswith("ey"):
            is_token = True
        else:
            raise ValueError()
    except Exception:
        await message.reply_text("❌ Usage: `/extract [api_url] [email]*[password]` OR `/extract [api_url] [JWT_Token]`")
        return

    status_msg = await message.reply_text("⏳ **Connecting to API...**")
    
    appx = AppxClient(base_url)
    if is_token:
        appx.token = creds
        try:
            import base64
            import json
            payload = creds.split('.')[1]
            payload += '=' * (-len(payload) % 4)
            appx.user_id = json.loads(base64.b64decode(payload).decode('utf-8')).get('id')
        except Exception as e:
            print(f"Token parse error: {e}")
    else:
        login_resp = appx.login(email, password)
        if not login_resp.get("success"):
            await status_msg.edit_text(f"❌ **Login Failed:** {login_resp.get('error')}")
            return
        
    app_name = base_url.split("//")[1].split(".")[0].upper().replace("API", "")
    token = appx.token
    courses_resp = appx.fetch_courses()
    
    if not courses_resp.get("success"):
        await status_msg.edit_text("❌ **Login succeeded, but failed to fetch courses.**")
        return
        
    courses = courses_resp.get("courses", [])
    courses_text = ""
    for c in courses:
        c_id = c.get("id", "N/A")
        c_title = c.get("title", c.get("CourseName", c.get("course_name", c.get("course_title", "Unknown"))))
        c_price = c.get("price", "0")
        courses_text += f"🆔 {c_id}  📚  {c_title}  💰 ₹{c_price}\n"
        
    success_msg = (
        f"✅ {app_name} Login Successfull !\n\n"
        f"🔗 API URL: {base_url}\n\n"
        f"🔑 Token: \n`{token}`\n\n"
        f"📚 Enrolled Courses List: \n\n"
        f"{courses_text}\n"
        f"**Reply to this message with the Course ID you want to extract.**"
    )
    
    if not hasattr(client, "user_sessions"):
        client.user_sessions = {}
        
    client.user_sessions[message.from_user.id] = {
        "appx": appx,
        "courses": courses,
        "app_name": app_name,
        "base_url": base_url
    }
    
    await status_msg.edit_text(success_msg)

from pyrogram.handlers import MessageHandler

@Client.on_message(filters.text & filters.private & ~filters.command(["start", "extract", "upload", "stop"]))
async def handle_course_selection(client: Client, message: Message):
    # if message.from_user.id not in AUTH_USERS:
    #     return
        
    if not hasattr(client, "user_sessions") or message.from_user.id not in client.user_sessions:
        return
        
    session = client.user_sessions[message.from_user.id]
    appx = session["appx"]
    courses = session["courses"]
    
    course_id = message.text.strip()
    
    selected_course = None
    for c in courses:
        if str(c.get("id")) == course_id:
            selected_course = c
            break
            
    if not selected_course:
        return
        
    import asyncio
    status_msg = await message.reply_text("⏳ **Extracting links... Please wait.**")
    
    start_time = time.time()
    links = await asyncio.to_thread(appx.extract_links, course_id)
    end_time = time.time()
    
    if not links:
        await status_msg.edit_text("❌ **No links found in this course.**")
        return
        
    c_title = selected_course.get("title", selected_course.get("CourseName", selected_course.get("name", "Unknown")))
    import re
    c_title = re.sub(r'[\\/*?:"<>| ]+', '_', c_title.strip())
    file_name = f"{c_title}.txt"
    
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(f"Course: {c_title}\n")
        f.write(f"BaseURL: {session['base_url']}\n\n")
        f.write("\n".join(links))
        
    total_time = end_time - start_time
    mins = int(total_time // 60)
    secs = int(total_time % 60)
    time_str = f"{mins}m {secs}s"
    
    dt_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    total_content = appx.total_videos + appx.total_pdfs
    
    caption = (
        f"✅ {session['app_name']} Login Successfull !\n\n"
        f"📚 Course Name:  {c_title}\n"
        f"• 🏛️ App Name: {session['app_name']}\n"
        f"• 📦 Batch ID: {course_id}\n"
        f"• 🌐 API Version: V2\n"
        f"• 💰 Price: ₹{selected_course.get('price', '0')}\n"
        f"• 🔗 API URL: {session['base_url']}\n"
        f"• 📦 Total Content: {total_content} | 🎥 Videos: {appx.total_videos}\n"
        f"• 📄 PDFs: {appx.total_pdfs} | 📦 Other: 0\n"
        f"• 🖼️ Thumbnail: Click Here To View\n"
        f"• ⏱️ Total Time Taken: {time_str}\n"
        f"• 📅 Date-Time: {dt_str}"
    )
    
    await client.send_document(
        chat_id=message.chat.id,
        document=file_name,
        caption=caption
    )
    
    await status_msg.delete()
    os.remove(file_name)
