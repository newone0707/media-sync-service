import urllib.request
import urllib.parse
import json
import ssl
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import time
import traceback
import re

def appx_login(base_url, email, password):
    base_url = base_url.rstrip('/')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    attempts = [
        # Strategy 1: v2 UrlEncoded (used by beingdoctorapi, sciencemagnet, kautilya)
        {
            "eps": ["/post/userLogin"],
            "data": f"email={urllib.parse.quote(email)}&password={urllib.parse.quote(password)}&device_type=WEB".encode('utf-8'),
            "ctype": "application/x-www-form-urlencoded"
        },
        # Strategy 2: JSON (used by genomicnursing)
        {
            "eps": ["/api/v2/users/login", "/api/users/login", "/v3/users/login", "/v2/users/login", "/users/login", "/get/loginWithEmail"],
            "data": json.dumps({"email": email, "password": password, "device_type": "WEB"}).encode('utf-8'),
            "ctype": "application/json"
        }
    ]
    
    got_404 = False
    
    for attempt in attempts:
        for ep in attempt["eps"]:
            url = base_url + ep
            # Some apps need version 3, some 2
            versions = ['2'] if attempt["ctype"] == "application/x-www-form-urlencoded" else ['3', '2']
            
            for v in versions:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                    'client-service': 'Appx',
                    'auth-key': 'appxapi',
                    'appx-version': v,
                    'device_type': 'WEB',
                    'Content-Type': attempt["ctype"]
                }
                try:
                    req = urllib.request.Request(url, data=attempt["data"], headers=headers, method='POST')
                    with urllib.request.urlopen(req, context=ctx, timeout=5) as res:
                        if res.status in [200, 203, 201]:
                            resp_json = json.loads(res.read().decode('utf-8'))
                            status_val = str(resp_json.get('status'))
                            if status_val in ["200", "1"] or resp_json.get('success'):
                                return {"success": True, "data": resp_json.get('data', resp_json), "endpoint": ep}
                            elif 'message' in resp_json:
                                return {"success": False, "error": resp_json['message']}
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        return {"success": False, "error": "Firewall Block! Please wait 15 minutes before trying again."}
                    if e.code == 404:
                        got_404 = True
                except Exception:
                    pass
                    
    if got_404:
        return {"success": False, "error": "Login failed (API might be blocked or URL is incorrect)."}
    return {"success": False, "error": "Login failed (Check credentials)."}

def appx_get_courses(base_url, token, user_id):
    base_url = base_url.rstrip('/')
    courses_endpoints = ["/get/mycoursev2", "/get/mycourses"]
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    tenant_match = re.search(r'https?://([a-zA-Z0-9-]+)(api)?\.', base_url)
    tenant_id = tenant_match.group(1).replace('api', '') if tenant_match else ""
    
    for v in ['3', '2']:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'appx-version': v,
            'client-service': 'Appx',
            'auth-key': 'appxapi',
            'device_type': 'WEB',
            'Authorization': token,
            'token': token,
            'User-ID': str(user_id)
        }
        for ep in courses_endpoints:
            url = base_url + ep
            if '?' in url:
                url += f"&userid={user_id}"
            else:
                url += f"?userid={user_id}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, context=ctx, timeout=5) as res:
                    if res.status == 200:
                        resp_json = json.loads(res.read().decode('utf-8'))
                        status_val = str(resp_json.get('status'))
                        if status_val in ["200", "1"] or resp_json.get('success'):
                            return {"success": True, "courses": resp_json.get('data', [])}
            except urllib.error.HTTPError as e:
                if e.code == 429: 
                    return {"success": False, "error": "Akamai WAF Rate Limit Block! Please wait 15 minutes before trying again."}
            except Exception: pass
            time.sleep(1)
            
    return {"success": False, "error": "Failed to fetch courses."}

def decrypt_val(encrypted_str, key_str="638udh3829162018", iv_str="fedcba9876543210"):
    try:
        parts = encrypted_str.split(':')
        ciphertext_b64 = parts[0]
        iv_bytes = base64.b64decode(parts[1]) if len(parts) > 1 else iv_str.encode('utf-8')
        ciphertext_bytes = base64.b64decode(ciphertext_b64)
        cipher = AES.new(key_str.encode('utf-8'), AES.MODE_CBC, iv=iv_bytes)
        return unpad(cipher.decrypt(ciphertext_bytes), AES.block_size).decode('utf-8')
    except Exception: return ""

def extract_batch_links(base_url, token, user_id, course_id, bot_instance=None, chat_id=None):
    base_url = base_url.rstrip('/')
    all_links = []
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'appx-version': '2',
        'client-service': 'Appx',
        'auth-key': 'appxapi',
        'device_type': 'WEB',
        'Authorization': token,
        'token': token,
        'User-ID': str(user_id)
    }
    
    def fetch_video_details(video_id):
        url = f"{base_url}/get/fetchVideoDetailsById?course_id={course_id}&video_id={video_id}&ytflag=1&folder_wise_course=1&userid={user_id}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=5) as res:
                if res.status == 200:
                    data = json.loads(res.read().decode('utf-8')).get('data', {})
                    
                    pdf_link = data.get('pdf_link')
                    if pdf_link:
                        if not pdf_link.startswith('http') and ':' in pdf_link:
                            dec = decrypt_val(pdf_link)
                            if dec: pdf_link = dec
                        return f"PDF: {pdf_link}"
                        
                    pdf_link2 = data.get('pdf_link2')
                    if pdf_link2:
                        if not pdf_link2.startswith('http') and ':' in pdf_link2:
                            dec = decrypt_val(pdf_link2)
                            if dec: pdf_link2 = dec
                        return f"PDF: {pdf_link2}"
                    
                    encrypted_links = data.get('encrypted_links', [])
                    # Sort links by quality preference to avoid 50MB limit (360p/480p preferred)
                    quality_order = {"360p": 1, "480p": 2, "240p": 3, "720p": 4, "1080p": 5}
                    encrypted_links.sort(key=lambda x: quality_order.get(x.get('quality', ''), 99))
                    
                    for link_obj in encrypted_links:
                        dec_link = decrypt_val(link_obj.get('path', ''))
                        if dec_link: return f"Video [{link_obj.get('quality', 'Unknown')}]: {dec_link}"
                        
                    if data.get('file_link'): return f"Video: {data['file_link']}"
        except Exception: pass
        return None

    def fetch_folder(parent_id, path_prefix=""):
        url = f"{base_url}/get/folder_contentsv2?course_id={course_id}&parent_id={parent_id}&folder_wise_course=1&userid={user_id}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=10) as res:
                if res.status == 200:
                    items = json.loads(res.read().decode('utf-8')).get('data', [])
                    for item in items:
                        title = item.get('Title', item.get('title', 'Unknown'))
                        item_type = item.get('resource_type', item.get('type'))
                        item_id = item.get('id')
                        
                        is_folder = str(item.get('is_folder')) == "1" or str(item_type) in ["2", "0"] or str(item.get('material_type')).upper() == "FOLDER"
                        if is_folder:
                            if bot_instance and chat_id:
                                try:
                                    bot_instance.send_message(chat_id, f"📂 Scanning folder: {title}")
                                except Exception: pass
                            fetch_folder(item_id, path_prefix + title + " > ")
                        else:
                            link_str = fetch_video_details(item_id)
                            if link_str: all_links.append(f"{path_prefix}{title}\n↳ {link_str}\n")
                            elif item.get('file_link') or item.get('pdf_link'):
                                link = item.get('file_link') or item.get('pdf_link')
                                all_links.append(f"{path_prefix}{title}\n↳ {link}\n")
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2)
        except Exception: pass

    fetch_folder("-1")
    return all_links
