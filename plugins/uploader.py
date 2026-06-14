import os
import time
import asyncio
import yt_dlp
import requests
from curl_cffi import requests as cffi_requests
from pyrogram import Client, filters
from pyrogram.types import Message
from utils import progress_bar, decrypt_file

# Global state to track uploads and stop requests
upload_states = {}
user_tokens = {}

import asyncio

def sync_download(url, output_path, referer):
    print(f"DEBUG sync_download URL: {url}")
    try:
        r = cffi_requests.get(url, stream=True, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': referer, 'Origin': referer})
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        with open('debug.log', 'a') as debug_f:
            debug_f.write(f"Direct Download Error: {e}\n")
        print(f"Direct Download Error: {e}")
        return False

async def download_m3u8(url, output_path, base_url, user_id=None):
    print(f"Downloading URL: {url}")
    referer = base_url if base_url.endswith('/') else base_url + '/'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': referer,
        'Origin': referer,
        'device-id': '39F093FF35F201D9'
    }
    
    if user_id and user_id in user_tokens:
        cp_token = user_tokens[user_id]
        if 'classplusapp' in url or "testbook.com" in url or "classplusapp.com/drm" in url or "media-cdn.classplusapp.com/drm" in url:
            try:
                if '&' in url:
                    url_part, contentId = url.split('&', 1)
                else:
                    url_part = url
                
                headers_api = {
                    'host': 'api.classplusapp.com',
                    'x-access-token': f'{cp_token}',    
                    'accept-language': 'EN',
                    'api-version': '18',
                    'app-version': '1.4.73.2',
                    'build-number': '35',
                    'connection': 'Keep-Alive',
                    'content-type': 'application/json',
                    'device-details': 'Xiaomi_Redmi 7_SDK-32',
                    'device-id': 'c28d3cb16bbdac01',
                    'region': 'IN',
                    'user-agent': 'Mobile-Android',
                    'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c',
                    'accept-encoding': 'gzip'
                }
                res = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url_part}', headers=headers_api)
                with open('debug.log', 'a') as f: f.write(f"JW API Status: {res.status_code}\nResult: {res.text}\n")
                
                if res.status_code == 200:
                    try:
                        new_url = res.json().get('data', {}).get('url')
                        if new_url:
                            url = new_url
                    except:
                        pass
                
                # In case jw-signed-url is just a distraction, let's also pass the token to yt-dlp headers:
                headers['x-access-token'] = cp_token
            except Exception as e:
                with open('debug.log', 'a') as f: f.write(f"JW Logic Error: {e}\n")

    if "token=" in url:
        token = url.split("token=")[1].split("&")[0]
        headers['x-access-token'] = token
        headers['api-version'] = "18"
        try:
            import base64
            import json
            payload = token.split(".")[1]
            padded = payload + "=" * ((4 - len(payload) % 4) % 4)
            jwt_data = json.loads(base64.b64decode(padded).decode("utf-8"))
            if "fingerprintId" in jwt_data:
                headers['device-id'] = jwt_data["fingerprintId"]
            else:
                headers['User-Agent'] = 'Mobile-Android'
                headers['app-version'] = '1.4.65.3'
        except:
            pass
    elif "appx" in url or "encrypted" in url:
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        if "appx" in referer:
            headers['Referer'] = referer
            headers['Origin'] = referer

    if "encrypted.mkv" in url or "encrypted.mp4" in url or ".zip" in url or "appx" in url:
        # Download directly via requests for direct files (in background thread)
        return await asyncio.to_thread(sync_download, url, output_path, referer)
    
    if "classplus" in url and "token=" in url:
        def sync_classplus_dl():
            try:
                import re
                import requests
                import urllib.parse
                
                nonlocal url
                token_match = re.search(r"token=([^&]+)", url)
                content_id_match = re.search(r"contentId=([^&]+)", url)
                course_id_match = re.search(r"courseId=([^&]+)", url)
                folder_id_match = re.search(r"folderId=([^&]+)", url)
                
                if token_match and content_id_match and course_id_match and folder_id_match:
                    token_val = token_match.group(1)
                    content_id = content_id_match.group(1)
                    course_id = course_id_match.group(1)
                    folder_id = folder_id_match.group(1)
                    
                    cp_headers = {
                        'host': 'api.classplusapp.com',
                        'x-access-token': token_val,
                        'accept-language': 'EN',
                        'api-version': '29',
                        'app-version': '1.4.65.3',
                        'device-id': '39F093FF35F201D9',
                        'user-agent': 'Mobile-Android'
                    }
                    
                    # Fetch the folder contents directly from Classplus API again
                    api_url = f"https://api.classplusapp.com/v2/course/content/get?courseId={course_id}&folderId={folder_id}"
                    resp = requests.get(api_url, headers=cp_headers)
                    if resp.status_code == 200:
                        res_json = resp.json()
                        items = res_json.get("data", {}).get("courseContent", [])
                        for item in items:
                            if str(item.get("id")) == str(content_id):
                                fresh_url = item.get("url")
                                fresh_hash = item.get("contentHashId")
                                if fresh_url and fresh_hash:
                                    encoded_hash = urllib.parse.quote(fresh_hash, safe="")
                                    url = f"{fresh_url}?contentHashId={encoded_hash}&token={token_val}"
                                break
                            
                r = requests.get(url, headers=headers)
                r.raise_for_status()
                master_text = r.text
                print("master_text length:", len(master_text))

                import urllib.parse
                base_url_hls = url.split("?")[0].rsplit("/", 1)[0] + "/"
                query_params = "?" + url.split("?")[1] if "?" in url else ""
                
                max_bw = 0
                best_res_url = None
                lines = master_text.splitlines()
                for j, line in enumerate(lines):
                    if line.startswith("#EXT-X-STREAM-INF"):
                        bw_match = re.search(r'BANDWIDTH=(\d+)', line)
                        bw = int(bw_match.group(1)) if bw_match else 0
                        if bw >= max_bw:
                            max_bw = bw
                            best_res_url = lines[j+1].strip()
                
                if best_res_url:
                    if not best_res_url.startswith("http"):
                        best_res_url = urllib.parse.urljoin(base_url_hls, best_res_url)
                    r2 = cffi_requests.get(best_res_url + query_params, headers=headers, impersonate='chrome')
                    r2.raise_for_status()
                    sub_text = r2.text
                    base_url_hls = best_res_url.split("?")[0].rsplit("/", 1)[0] + "/"
                else:
                    sub_text = master_text
                    
                new_lines = []
                for line in sub_text.splitlines():
                    if line.startswith("#EXT-X-KEY"):
                        uri_match = re.search(r'URI="([^"]+)"', line)
                        if uri_match:
                            uri = uri_match.group(1)
                            abs_uri = urllib.parse.urljoin(base_url_hls, uri) if not uri.startswith("http") else uri
                            line = line.replace(f'URI="{uri}"', f'URI="{abs_uri}{query_params}"')
                        new_lines.append(line)
                    elif line and not line.startswith("#"):
                        abs_line = urllib.parse.urljoin(base_url_hls, line) if not line.startswith("http") else line
                        new_lines.append(abs_line + query_params)
                    else:
                        new_lines.append(line)
                        
                local_m3u8 = output_path + ".m3u8"
                with open(local_m3u8, "w") as f:
                    f.write("\n".join(new_lines))
                    
                ydl_opts_local = {
                    'format': 'best',
                    'outtmpl': output_path,
                    'quiet': False,
                    'no_warnings': False,
                    'http_headers': headers
                }
                with yt_dlp.YoutubeDL(ydl_opts_local) as ydl:
                    ret = ydl.download([local_m3u8])
                    
                if os.path.exists(local_m3u8):
                    os.remove(local_m3u8)
                    
                return ret == 0
            except Exception as e:
                import traceback
                print(f"Classplus Custom DL Error:\n{traceback.format_exc()}")
                return False
        return await asyncio.to_thread(sync_classplus_dl)

    ydl_opts = {
        'format': 'best',
        'outtmpl': output_path,
        'quiet': False,
        'no_warnings': False,
        'http_headers': headers
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ret = ydl.download([url])
            return ret == 0
    except Exception as e:
        import traceback
        print(f"YT-DLP Error:\n{traceback.format_exc()}")
        return False


@Client.on_message(filters.command("token") & filters.private)
async def token_cmd(client: Client, message: Message):
    parts = message.text.split(" ", 1)
    if len(parts) > 1:
        user_tokens[message.from_user.id] = parts[1].strip()
        await message.reply_text("Updated Token Used ✅")
    else:
        await message.reply_text("Please provide a token. Usage: /token <token>")

@Client.on_message(filters.command("stop") & filters.private)
async def stop_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in upload_states and upload_states[user_id].get("is_uploading"):
        upload_states[user_id]["stop_requested"] = True
        await message.reply_text("🛑 **Stop requested! The process will halt after the current file finishes.**")
    else:
        await message.reply_text("❌ **No upload process is currently running.**")

@Client.on_message(filters.command("upload") & filters.private)
async def upload_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    
    parts = message.text.split(" ")
    limit = 0
    if len(parts) > 1:
        if parts[1].isdigit():
            limit = int(parts[1])
        elif parts[1].lower() == "all":
            limit = -1
        else:
            await message.reply_text("❌ **Usage:** `/upload [count]` or `/upload all`")
            return
    else:
        await message.reply_text("❌ **Usage:** `/upload [count]` or `/upload all`")
        return
        
    upload_states[user_id] = {
        "waiting_for_file": True,
        "limit": limit,
        "is_uploading": False,
        "stop_requested": False
    }
    
    await message.reply_text(f"✅ **Ready to upload {limit if limit > 0 else 'ALL'} links!**\n\n📄 **Please send me the `.txt` file containing the extracted links now.**")

@Client.on_message(filters.document & filters.private)
async def handle_document(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in upload_states or not upload_states[user_id].get("waiting_for_file"):
        return
        
    doc = message.document
    if not doc.file_name.endswith('.txt'):
        await message.reply_text("❌ **Please send a valid `.txt` file.**")
        return
        
    state = upload_states[user_id]
    state["waiting_for_file"] = False
    state["is_uploading"] = True
    state["stop_requested"] = False
    limit = state["limit"]
    
    status_msg = await message.reply_text("⏳ **Downloading and parsing your file...**")
    file_data = await message.download(in_memory=True)
    
    try:
        content = file_data.getvalue().decode("utf-8")
        lines = content.splitlines(True)
    except Exception as e:
        await status_msg.edit_text(f"❌ **Failed to read file:** {e}")
        state["is_uploading"] = False
        return
    finally:
        pass

    links_to_upload = []
    base_url = "https://web.classplusapp.com/"
    for line in lines:
        line = line.strip()
        if not line or line.startswith("Course:"):
            continue
        if line.startswith("BaseURL:"):
            base_url = line.split("BaseURL:")[1].strip()
            continue
        if ": " in line:
            name, link = line.split(": ", 1)
            if link.startswith("http"):
                links_to_upload.append({"name": name.strip(), "link": link.strip()})
        elif line.startswith("http"):
             links_to_upload.append({"name": "Video", "link": line.strip()})

    if limit > 0:
        links_to_upload = links_to_upload[:limit]

    if not links_to_upload:
        await status_msg.edit_text("❌ **No valid links found in the file.**")
        state["is_uploading"] = False
        return

    await status_msg.edit_text(f"🚀 **Found {len(links_to_upload)} links. Starting upload process...**\n\n*(Send /stop anytime to halt)*")

    uploaded_count = 0
    for i, item in enumerate(links_to_upload):
        if state["stop_requested"]:
            await message.reply_text("🛑 **Process stopped by user!**")
            break
            
        name = item["name"]
        link = item["link"]
        prog_msg = await message.reply_text(f"⏳ **Processing {i+1}/{len(links_to_upload)}:**\n`{name}`")
        
        if ".pdf" in link.lower() or "pdf" in name.lower():
            # Download PDF
            await prog_msg.edit_text(f"⏳ **Downloading PDF:**\n`{name}`")
            pdf_path = f"{name}.pdf"
            import re
            pdf_path = re.sub(r'[\\/*?:"<>|]', '_', pdf_path) # sanitize
            
            aes_key = None
            if ":Zm" in link or ":" in link.split("/")[-1]:
                parts = link.rsplit(":", 1)
                if len(parts) == 2 and len(parts[1]) > 10 and "=" in parts[1]:
                    link, aes_key = parts
            elif "*" in link:
                parts = link.rsplit("*", 1)
                if len(parts) == 2 and len(parts[1]) > 10 and "=" in parts[1]:
                    link, aes_key = parts

            def sync_pdf_dl(actual_link):
                try:
                    h = {'User-Agent': 'Mozilla/5.0', 'device-id': '39F093FF35F201D9'}
                    if "token=" in actual_link:
                        token = link.split("token=")[1].split("&")[0]
                        h['x-access-token'] = token
                        h['api-version'] = "18"
                        try:
                            import base64
                            import json
                            payload = token.split(".")[1]
                            padded = payload + "=" * ((4 - len(payload) % 4) % 4)
                            jwt_data = json.loads(base64.b64decode(padded).decode("utf-8"))
                            if "fingerprintId" in jwt_data:
                                h['device-id'] = jwt_data["fingerprintId"]
                            else:
                                h['User-Agent'] = 'Mobile-Android'
                                h['app-version'] = '1.4.65.3'
                        except:
                            pass
                    r = cffi_requests.get(actual_link, stream=True, headers=h)
                    r.raise_for_status()
                    with open(pdf_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return True
                except Exception as e:
                    with open('debug.log', 'a') as debug_f:
                        debug_f.write(f"PDF Download Error: {e}\n")
                    print(f"PDF Download Error: {e}")
                    return False
            success = await asyncio.to_thread(sync_pdf_dl, link)
            
            if success and aes_key and os.path.exists(pdf_path):
                decrypted = decrypt_file(pdf_path, aes_key)
                if not decrypted:
                    success = False

            if state["stop_requested"]:
                break
                
            if success:
                start_time = time.time()
                try:
                    await client.send_document(
                        chat_id=message.chat.id,
                        document=pdf_path,
                        caption=f"📄 **{name}**",
                        progress=progress_bar,
                        progress_args=(prog_msg, start_time)
                    )
                    await prog_msg.delete()
                    uploaded_count += 1
                except Exception as e:
                    with open('debug.log', 'a') as debug_f:
                        debug_f.write(f"Upload Error: {e}\n")
                    await prog_msg.edit_text(f"❌ **Failed to upload PDF:**\n`{e}`")
            else:
                await prog_msg.edit_text(f"❌ **Failed to download PDF:**\n`{name}`")
            
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        else:
            # Download Video
            await prog_msg.edit_text(f"⏳ **Downloading Video (This may take a while):**\n`{name}`")
            import re
            mp4_path = f"{name}.mp4"
            mp4_path = re.sub(r'[\\/*?:"<>|]', '_', mp4_path)
            
            aes_key = None
            if ":Zm" in link or ":" in link.split("/")[-1]: # Appx AES keys often start with Zm or are appended with :
                parts = link.rsplit(":", 1)
                if len(parts) == 2 and len(parts[1]) > 10 and "=" in parts[1]:
                    link, aes_key = parts
            elif "*" in link:
                parts = link.rsplit("*", 1)
                if len(parts) == 2 and len(parts[1]) > 10 and "=" in parts[1]:
                    link, aes_key = parts
            
            success = await download_m3u8(link, mp4_path, base_url)
            
            if success and aes_key and os.path.exists(mp4_path):
                await prog_msg.edit_text(f"⏳ **Decrypting Video...**\n`{name}`")
                decrypted = decrypt_file(mp4_path, aes_key)
                if not decrypted:
                    success = False
            
            if state["stop_requested"]:
                if os.path.exists(mp4_path):
                    os.remove(mp4_path)
                break
                
            if success and os.path.exists(mp4_path):
                start_time = time.time()
                try:
                    parts = [p.strip() for p in name.split(">")]
                    video_title = parts[-1]
                    topic_name = parts[-2] if len(parts) > 1 else "Home"
                    batch_name = parts[1] if len(parts) > 2 else (parts[0] if len(parts) > 0 else "Unknown")
                    vid_id = f"{i+1:03d}"
                    
                    custom_caption = f"""[🎥] **Vid Id** : `{vid_id}`\n**Video Title** : `{video_title}`\n**Topic Name** : `{topic_name}`\n**Batch Name** : `{batch_name}`\n\n**Extracted By** ➢ Clean Leach Bot"""
                    
                    # Extract Metadata
                    thumb_path = f"{mp4_path}.jpg"
                    duration, width, height = 0, 0, 0
                    try:
                        import subprocess, json
                        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", mp4_path]
                        res = await asyncio.to_thread(subprocess.check_output, cmd, stderr=subprocess.STDOUT)
                        meta = json.loads(res.decode("utf-8"))
                        duration = int(float(meta.get("format", {}).get("duration", 0)))
                        for stream in meta.get("streams", []):
                            if stream.get("codec_type") == "video":
                                width = int(stream.get("width", 0))
                                height = int(stream.get("height", 0))
                                break
                        thumb_cmd = ["ffmpeg", "-y", "-i", mp4_path, "-ss", "00:00:02.000", "-vframes", "1", thumb_path]
                        await asyncio.to_thread(subprocess.check_output, thumb_cmd, stderr=subprocess.STDOUT)
                        if not os.path.exists(thumb_path): thumb_path = None
                    except:
                        thumb_path = None
                    
                    await client.send_video(
                        chat_id=message.chat.id,
                        video=mp4_path,
                        caption=custom_caption,
                        supports_streaming=True,
                        duration=duration,
                        width=width,
                        height=height,
                        thumb=thumb_path,
                        progress=progress_bar,
                        progress_args=(prog_msg, start_time)
                    )
                    if thumb_path and os.path.exists(thumb_path):
                        os.remove(thumb_path)
                    await prog_msg.delete()
                    uploaded_count += 1
                except Exception as e:
                    with open('debug.log', 'a') as debug_f:
                        debug_f.write(f"Video Upload Error: {e}\n")
                    await prog_msg.edit_text(f"❌ **Failed to upload:**\n`{e}`")
                finally:
                    if os.path.exists(mp4_path):
                        os.remove(mp4_path)
            else:
                await prog_msg.edit_text(f"❌ **Failed to download Video:**\n`{name}`")

    state["is_uploading"] = False
    await message.reply_text(f"✅ **Finished! Successfully processed {uploaded_count} files.**")
