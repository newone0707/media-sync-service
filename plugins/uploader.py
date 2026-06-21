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
spayee_clients = {}

import asyncio

def sync_download(url, output_path, referer):
    print(f"DEBUG sync_download URL: {url}")
    try:
        ref_header = referer + "/" if referer and not referer.endswith("/") else referer
        origin_header = referer[:-1] if referer and referer.endswith("/") else referer
        r = cffi_requests.get(url, stream=True, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': ref_header, 'Origin': origin_header}, impersonate="chrome")
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

async def download_m3u8(url, output_path, base_url, user_id=None, spayee_token=None):
    print(f"Downloading URL: {url}")
    referer = base_url if base_url.endswith('/') else base_url + '/'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': referer,
        'Origin': referer,
        'device-id': '39F093FF35F201D9'
    }
    
    if spayee_token and spayee_token != 'NO_TOKEN':
        headers['Authorization'] = f'Bearer {spayee_token}'
        headers['X-Auth-Token'] = spayee_token
        headers['Cookie'] = f'c_ujwt={spayee_token}; jwt={spayee_token}'
    
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
    elif "appx" in url or "classx" in url or "akamai" in url or "encrypted" in url:
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        headers['Referer'] = referer
        headers['Origin'] = referer.rstrip('/')

    if "encrypted.mkv" in url or "encrypted.mp4" in url or ".zip" in url or "appx" in url or "classx" in url or "akamai" in url:
        # Download directly via curl_cffi Chrome impersonation (works for AppX/ClassX CDN)
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
                        'api-version': '18',
                        'app-version': '1.4.73.2',
                        'device-id': 'c28d3cb16bbdac01',
                        'user-agent': 'Mobile-Android'
                    }
                    
                    try:
                        jw_res = requests.get('https://api.classplusapp.com/cams/uploader/video/jw-signed-url', headers=cp_headers, params={'contentId': content_id, 'offlineDownload': 'false'})
                        if jw_res.status_code == 200 and 'url' in jw_res.json():
                            url = jw_res.json()['url']
                    except Exception as e:
                        print("Failed JW signed URL:", e)
                    
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
                    
                import subprocess
                ffmpeg_cmd = [
                    'ffmpeg', '-y',
                    '-headers', "".join([f"{k}: {v}\r\n" for k, v in headers.items()]),
                    '-allowed_extensions', 'ALL',
                    '-protocol_whitelist', 'file,http,https,tcp,tls,crypto',
                    '-i', local_m3u8,
                    '-c', 'copy',
                    output_path
                ]
                
                try:
                    subprocess.run(ffmpeg_cmd, check=True)
                    ret = 0
                except subprocess.CalledProcessError:
                    ret = 1
                    
                if os.path.exists(local_m3u8):
                    os.remove(local_m3u8)
                    
                return ret == 0
            except Exception as e:
                import traceback
                print(f"Classplus Custom DL Error:\n{traceback.format_exc()}")
                return False
        return await asyncio.to_thread(sync_classplus_dl)

    if spayee_token and spayee_token != 'NO_TOKEN':
        def sync_spayee_dl():
            try:
                import re
                import os
                import urllib.parse
                from curl_cffi import requests as cffi_requests
                
                user_provided_key = None
                if 'HLS_KEY=' in url:
                    parts = url.split('HLS_KEY=')
                    url = parts[0]
                    user_provided_key = bytes.fromhex(parts[1].strip())
                raw_url = url
                _spayee_token = spayee_token
                spayee_key_b64 = None
                referer_origin = 'https://www.rglectures.com'
                if '*' in _spayee_token:
                    parts = _spayee_token.split('*')
                    _spayee_token = parts[0]
                    if len(parts) > 1:
                        spayee_key_b64 = parts[1]
                    if len(parts) > 2:
                        referer_origin = parts[2]
                
                ts_urls = []
                base_url_hls = url.split("?")[0].rsplit("/", 1)[0] + "/"
                headers_spayee = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                    'Authorization': f'Bearer {_spayee_token}',
                    'Cookie': f'c_ujwt={_spayee_token}; jwt={_spayee_token}',
                    'Referer': base_url_hls,
                    'Origin': referer_origin,
                }
                
                print(f"[Spayee] Fetching Master M3U8...", flush=True)
                r = cffi_requests.get(url, headers=headers_spayee, impersonate='chrome', timeout=15)
                if r.status_code != 200:
                    err_msg = f"Spayee Master M3U8 Error: HTTP {r.status_code}\nThis usually means the link has EXPIRED. Please extract fresh links!"
                    print(err_msg)
                    return err_msg
                    
                master_text = r.text
                base_url_hls = url.split("?")[0].rsplit("/", 1)[0] + "/"
                
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
                    print(f"[Spayee] Fetching Chunk M3U8...", flush=True)
                    r2 = cffi_requests.get(best_res_url, headers=headers_spayee, impersonate='chrome', timeout=15)
                    sub_text = r2.text
                    base_url_hls = best_res_url.split("?")[0].rsplit("/", 1)[0] + "/"
                else:
                    sub_text = master_text
                    
                import uuid
                from Crypto.Cipher import AES
                rand_id = uuid.uuid4().hex
                new_lines = []
                local_key_path = f"spayee_{rand_id}.key"
                
                # Pre-fetch the first TS segment and the IV for brute-forcing
                first_ts_url = None
                iv_hex = None
                for line in sub_text.splitlines():
                    if line.startswith("#EXT-X-KEY"):
                        iv_match = re.search(r'IV=0x([0-9a-fA-F]+)', line)
                        if iv_match:
                            iv_hex = iv_match.group(1)
                    elif line and not line.startswith("#"):
                        first_ts_url = urllib.parse.urljoin(base_url_hls, line) if not line.startswith("http") else line
                        break
                
                for line in sub_text.splitlines():
                    if line.startswith("#EXT-X-KEY"):
                        uri_match = re.search(r'URI="([^"]+)"', line)
                        if uri_match:
                            uri = uri_match.group(1)
                            abs_uri = urllib.parse.urljoin(base_url_hls, uri) if not uri.startswith("http") else uri
                            
                            # Fetch TS for validation
                            print(f"[Spayee] Fetching first TS...", flush=True)
                            r_ts = cffi_requests.get(first_ts_url, headers=headers_spayee, impersonate="chrome", timeout=15)
                            if b"<html" in r_ts.content[:500].lower() or b"cloudflare" in r_ts.content[:500].lower():
                                raise Exception("Cloudflare blocked TS download! Returned HTML challenge.")
                                
                            # Increase blob size to 4000 to bypass large ID3 tags but remain fast
                            ts_blob = r_ts.content[:4000]
                            # Make sure it's a multiple of 16
                            if len(ts_blob) % 16 != 0:
                                ts_blob = ts_blob[:-(len(ts_blob) % 16)]
                                
                            # Extract media sequence from URL if possible
                            test_seq = 0
                            import re
                            seq_match = re.search(r'_0*(\d+)\.ts', first_ts_url.split("?")[0])
                            if seq_match:
                                test_seq = int(seq_match.group(1))
                                
                            iv = bytes.fromhex(iv_hex) if iv_hex else test_seq.to_bytes(16, 'big')
                            
                            # Extract JWT claims for Spayee's 3-part XOR derivation
                            p_bytes, e_bytes = b'', b''
                            try:
                                import json, base64
                                payload_b64 = _spayee_token.split('.')[1]
                                pad = len(payload_b64) % 4
                                if pad: payload_b64 += '=' * (4 - pad)
                                payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
                                def safe_b64decode(s):
                                    if isinstance(s, str): s = s.encode()
                                    pad = len(s) % 4
                                    if pad: s += b'=' * (4 - pad)
                                    return base64.urlsafe_b64decode(s)
                                p_bytes = safe_b64decode(payload.get('p', ''))
                                e_bytes = safe_b64decode(payload.get('e', ''))
                            except Exception as err:
                                jwt_error = str(err)
                                print(f"[Spayee] Failed to parse JWT claims: {err}", flush=True)

                            decrypted_key = None
                            if user_provided_key:
                                decrypted_key = user_provided_key
                                print("[Spayee] Using User-Provided HLS_KEY!", flush=True)
                            key_blob = None
                            key_blobs_to_test = []
                            if spayee_key_b64:
                                try:
                                    import base64
                                    key_blobs_to_test.append(base64.b64decode(spayee_key_b64))
                                except: pass
                            
                            if not key_blobs_to_test:
                                print(f"[Spayee] Fetching key blob from: {abs_uri[:80]}", flush=True)
                                for _ in range(5):
                                    r_key = cffi_requests.get(abs_uri, headers=headers_spayee, impersonate="chrome", timeout=15)
                                    if r_key.status_code != 200:
                                        print(f"[Spayee] Key fetch returned status: {r_key.status_code}", flush=True)
                                    if len(r_key.content) in (16, 64):
                                        key_blobs_to_test.append(r_key.content)
                                        break

                            # Sync byte check helper
                            def verify_key(k):
                                if not ts_blob or len(ts_blob) < 1000:
                                    return False
                                try:
                                    c = AES.new(k, AES.MODE_CBC, iv=iv)
                                    d = c.decrypt(ts_blob)
                                    # Fast path: find 'G' (0x47) in C
                                    idx = d.find(0x47)
                                    while idx != -1 and idx <= len(d) - 940:
                                        if d[idx+188] == 0x47 and d[idx+376] == 0x47 and d[idx+564] == 0x47 and d[idx+752] == 0x47 and d[idx+940] == 0x47:
                                            return True
                                        idx = d.find(0x47, idx + 1)
                                except:
                                    pass
                                return False

                            for key_blob in key_blobs_to_test:
                                if decrypted_key: break
                                if len(key_blob) != 64: continue
                                
                                # 1. Try plain slices
                                for offset in range(len(key_blob) - 15):
                                    k = key_blob[offset:offset+16]
                                    if verify_key(k):
                                        decrypted_key = k
                                        print(f"[Spayee] Decrypted key match at plain offset: {offset}", flush=True)
                                        break
                                        
                                # 2. Try Token XOR
                                if not decrypted_key:
                                    t_bytes = _spayee_token.encode()
                                    for k_off in range(len(key_blob) - 15):
                                        if decrypted_key: break
                                        for t_off in range(len(t_bytes) - 15):
                                            k = bytes([a ^ b for a, b in zip(key_blob[k_off:k_off+16], t_bytes[t_off:t_off+16])])
                                            if verify_key(k):
                                                decrypted_key = k
                                                print(f"[Spayee] Decrypted key match at Token XOR: k={k_off}, t={t_off}", flush=True)
                                                break
                                                
                                # 3. Try p/e XOR
                                if not decrypted_key and p_bytes and e_bytes:
                                    for k_off in range(len(key_blob) - 15):
                                        if decrypted_key: break
                                        for p_off in range(len(p_bytes) - 15):
                                            if decrypted_key: break
                                            for e_off in range(len(e_bytes) - 15):
                                                pe = bytes([a^b for a,b in zip(p_bytes[p_off:p_off+16], e_bytes[e_off:e_off+16])])
                                                k = bytes([a^b for a,b in zip(key_blob[k_off:k_off+16], pe)])
                                                if verify_key(k):
                                                    decrypted_key = k
                                                    print(f"[Spayee] Decrypted key match at p/e XOR: k={k_off}, p={p_off}, e={e_off}", flush=True)
                                                    break
                                                    
                                # 4. Try p/e/t XOR (newest Spayee obfuscation)
                                if not decrypted_key and p_bytes and e_bytes and t_bytes:
                                    for k_off in range(len(key_blob) - 15):
                                        if decrypted_key: break
                                        for p_off in range(len(p_bytes) - 15):
                                            if decrypted_key: break
                                            for e_off in range(len(e_bytes) - 15):
                                                if decrypted_key: break
                                                for t_off in range(len(t_bytes) - 15):
                                                    pe = bytes([a^b for a,b in zip(p_bytes[p_off:p_off+16], e_bytes[e_off:e_off+16])])
                                                    pet = bytes([a^b for a,b in zip(pe, t_bytes[t_off:t_off+16])])
                                                    k = bytes([a^b for a,b in zip(key_blob[k_off:k_off+16], pet)])
                                                    if verify_key(k):
                                                        decrypted_key = k
                                                        print(f"[Spayee] Decrypted key match at p/e/t XOR: k={k_off}, p={p_off}, e={e_off}, t={t_off}", flush=True)
                                                        break

                                # 5. Try just p XOR or e XOR or p/t or e/t
                                if not decrypted_key:
                                    for k_off in range(len(key_blob) - 15):
                                        if decrypted_key: break
                                        if p_bytes:
                                            for p_off in range(len(p_bytes) - 15):
                                                k = bytes([a^b for a,b in zip(key_blob[k_off:k_off+16], p_bytes[p_off:p_off+16])])
                                                if verify_key(k):
                                                    decrypted_key, print_msg = k, f"[Spayee] Decrypted key match at p XOR: k={k_off}, p={p_off}"
                                                    break
                                        if decrypted_key: print(print_msg, flush=True); break
                                        if e_bytes:
                                            for e_off in range(len(e_bytes) - 15):
                                                k = bytes([a^b for a,b in zip(key_blob[k_off:k_off+16], e_bytes[e_off:e_off+16])])
                                                if verify_key(k):
                                                    decrypted_key, print_msg = k, f"[Spayee] Decrypted key match at e XOR: k={k_off}, e={e_off}"
                                                    break
                                        if decrypted_key: print(print_msg, flush=True); break
                                        if p_bytes and t_bytes:
                                            for p_off in range(len(p_bytes) - 15):
                                                if decrypted_key: break
                                                for t_off in range(len(t_bytes) - 15):
                                                    pt = bytes([a^b for a,b in zip(p_bytes[p_off:p_off+16], t_bytes[t_off:t_off+16])])
                                                    k = bytes([a^b for a,b in zip(key_blob[k_off:k_off+16], pt)])
                                                    if verify_key(k):
                                                        decrypted_key, print_msg = k, f"[Spayee] Decrypted key match at p/t XOR: k={k_off}, p={p_off}, t={t_off}"
                                                        break
                                        if decrypted_key: print(print_msg, flush=True); break
                                        if e_bytes and t_bytes:
                                            for e_off in range(len(e_bytes) - 15):
                                                if decrypted_key: break
                                                for t_off in range(len(t_bytes) - 15):
                                                    et = bytes([a^b for a,b in zip(e_bytes[e_off:e_off+16], t_bytes[t_off:t_off+16])])
                                                    k = bytes([a^b for a,b in zip(key_blob[k_off:k_off+16], et)])
                                                    if verify_key(k):
                                                        decrypted_key, print_msg = k, f"[Spayee] Decrypted key match at e/t XOR: k={k_off}, e={e_off}, t={t_off}"
                                                        break
                                        if decrypted_key: print(print_msg, flush=True); break
                            if decrypted_key:
                                # DO NOT WRITE KEY FILE
                                pass
                            elif key_blob and len(key_blob) == 64:
                                debug_info = f"Spayee Decryption Failed!\nTS Status: {r_ts.status_code}\nTS Len: {len(ts_blob) if ts_blob else 0}\np:{len(p_bytes)} e:{len(e_bytes)} t:{len(t_bytes)}\nJWT Error: {jwt_error if 'jwt_error' in locals() else 'None'}"
                                raise Exception(debug_info)
                            elif key_blob and len(key_blob) == 16:
                                # Unobfuscated 16-byte key
                                print(f"[Spayee] Direct 16-byte key found", flush=True)
                                decrypted_key = key_blob
                            else:
                                raise Exception("Key blob missing or invalid length.")
                        # SKIP ADDING EXT-X-KEY TO M3U8
                        pass
                    elif line and not line.startswith("#"):
                        abs_line = urllib.parse.urljoin(base_url_hls, line) if not line.startswith("http") else line
                        ts_urls.append(abs_line)
                        local_ts_path = f"chunk_{len(ts_urls)-1}.ts"
                        new_lines.append(local_ts_path)
                    else:
                        new_lines.append(line)
                        
                ts_dir = f"temp_ts_{rand_id}"
                os.makedirs(ts_dir, exist_ok=True)
                
                # Parse media sequence for IV
                media_sequence = 0
                for line in sub_text.splitlines():
                    if line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
                        try:
                            media_sequence = int(line.split(":")[1].strip())
                        except: pass
                        break
                        
                # If sequence is 0, check the first TS URL just in case the M3U8 omitted it
                if media_sequence == 0 and len(ts_urls) > 0:
                    import re
                    seq_match = re.search(r'_0*(\d+)\.ts', ts_urls[0].split("?")[0])
                    if seq_match:
                        media_sequence = int(seq_match.group(1))
                
                # Download all TS chunks concurrently using cffi_requests
                import concurrent.futures
                
                def download_single_ts(idx_url):
                    idx, ts_url = idx_url
                    chunk_path = os.path.join(ts_dir, f"chunk_{idx}.ts")
                    for _ in range(5):
                        try:
                            resp = cffi_requests.get(ts_url, headers=headers_spayee, impersonate="chrome", timeout=15)
                            if resp.status_code == 200:
                                ts_data = resp.content
                                if decrypted_key:
                                    current_iv = bytes.fromhex(iv_hex) if iv_hex else (media_sequence + idx).to_bytes(16, 'big')
                                    if len(ts_data) % 16 != 0:
                                        ts_data = ts_data[:-(len(ts_data) % 16)]
                                    c = AES.new(decrypted_key, AES.MODE_CBC, iv=current_iv)
                                    ts_data = c.decrypt(ts_data)
                                    
                                    # Fallback: forcefully drop the first 188 bytes (1 TS packet) to bypass any lingering IV corruption
                                    # This guarantees FFMPEG won't crash on 'Invalid data found' due to a corrupted PAT/PMT/ID3 header
                                    if idx == 0 and len(ts_data) > 188:
                                        ts_data = ts_data[188:]
                                    
                                with open(chunk_path, "wb") as f:
                                    f.write(ts_data)
                                return True
                        except:
                            import time
                            time.sleep(1)
                    return False
                
                print(f"[Spayee] Downloading and decrypting {len(ts_urls)} TS chunks via Python...", flush=True)
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    results = list(executor.map(download_single_ts, enumerate(ts_urls)))
                
                if not all(results):
                    raise Exception("Failed to download one or more TS chunks!")
                
                # Verify chunk sizes
                for i in range(len(ts_urls)):
                    chunk_path = os.path.join(ts_dir, f"chunk_{i}.ts")
                    if os.path.exists(chunk_path):
                        if os.path.getsize(chunk_path) == 0:
                            raise Exception(f"TS chunk {i} is 0 bytes! CDN blocked it.")
                    else:
                        raise Exception(f"TS chunk {i} is missing!")
                
                local_m3u8 = os.path.join(ts_dir, f"spayee_{rand_id}.m3u8")
                with open(local_m3u8, "w", encoding='utf-8') as f:
                    f.write("\n".join(new_lines))
                    
                import subprocess
                ffmpeg_cmd = [
                    'ffmpeg', '-y',
                    '-allowed_extensions', 'ALL',
                    '-protocol_whitelist', 'file,http,https,tcp,tls,crypto',
                    '-i', local_m3u8,
                    '-c', 'copy',
                    output_path
                ]
                
                try:
                    res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                    if res.returncode != 0:
                        ret = 1
                        err_text = res.stderr[-800:] if res.stderr else "Unknown FFMPEG Error"
                        print(f"FFMPEG ERROR: {err_text}", flush=True)
                        error_msg = f"FFMPEG Error:\n{err_text}"
                    else:
                        ret = 0
                        error_msg = None
                except Exception as ex:
                    ret = 1
                    error_msg = f"Subprocess Error: {str(ex)}"
                    
                if os.path.exists(local_key_path): os.remove(local_key_path)
                import shutil
                if os.path.exists(ts_dir): shutil.rmtree(ts_dir)
                    
                if ret != 0:
                    return error_msg
                return True
            except Exception as e:
                import traceback
                print(f"Spayee Custom DL Error:\\n{traceback.format_exc()}")
                return False
        return await asyncio.to_thread(sync_spayee_dl)

    from yt_dlp.networking.impersonate import ImpersonateTarget
    ydl_opts = {
        'outtmpl': output_path,
        'quiet': False,
        'no_warnings': False,
        'http_headers': headers,
        'abort_on_error': False,
        'impersonate': ImpersonateTarget(client='chrome')
    }
    
    # Try getting ffmpeg path safely in case it's an m3u8 stream
    import shutil
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        ydl_opts['ffmpeg_location'] = ffmpeg_path
        
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

    import re as _re
    links_to_upload = []
    raw_base_url = "https://web.classplusapp.com"
    for line in lines:
        line = line.strip()
        if not line or line.startswith("Course:") or line.startswith("URL:"):
            continue
        if line.startswith("BaseURL:"):
            raw_base_url = line.split("BaseURL:")[1].strip()
            continue
        # Skip encrypted blob lines like: Video: UXWcDRZQ65VRP...
        if _re.match(r'^(Home\s*>.*>\s*)?Video:\s*[A-Za-z0-9+/]{20}', line):
            continue
        if ": " in line:
            name, link = line.rsplit(": ", 1)
            if link.startswith("http"):
                links_to_upload.append({"name": name.strip(), "link": link.strip()})
        elif line.startswith("http"):
             links_to_upload.append({"name": "Video", "link": line.strip()})

    # Build correct referer: strip 'api' suffix, add trailing slash
    # e.g. https://newchandanlogicsapi.classx.co.in -> https://newchandanlogics.classx.co.in/
    # Also handles akamai.net.in, appx.co.in etc.
    _m = _re.match(r'(https?://)([^.]+?)(api)?\.(.+)$', raw_base_url, _re.IGNORECASE)
    if _m:
        base_url = f"{_m.group(1)}{_m.group(2)}.{_m.group(4)}/"
    else:
        base_url = raw_base_url.rstrip('/') + '/'

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
        
        # Token & AES Key extraction must happen first so we can check the real extension
        aes_key = None
        spayee_token = None
        
        if "PSWD=" in link:
            parts = link.split("PSWD=")
            link = parts[0]
            aes_key = parts[1].strip()

        # Clean the link for extension detection
        clean_link = link.split("*")[0] if "*" in link else link
        _link_path = clean_link.split("?")[0].lower()
        
        is_video = any(ext in _link_path for ext in [".m3u8", ".mp4", ".mkv", "youtube.com", "youtu.be"])
        if _link_path.endswith(".pdf") or (not is_video and "pdf" in name.lower()):
            # Download PDF
            await prog_msg.edit_text(f"⏳ **Downloading PDF:**\n`{name}`")
            pdf_path = f"{name}.pdf"
            import re
            pdf_path = re.sub(r'[\\/*?:"<>|]', '_', pdf_path) # sanitize
            
            is_appx = "appx" in clean_link or "classx" in clean_link or "akamai" in clean_link or "encrypted" in clean_link
            
            if "*" in link:
                star_parts = link.split("*", 1)
                link = star_parts[0]
                if is_appx:
                    aes_key = star_parts[1]
                else:
                    spayee_token = star_parts[1]
            elif ":Zm" in link or ":" in link.split("/")[-1]:
                parts = link.rsplit(":", 1)
                if len(parts) == 2 and len(parts[1]) > 10 and "=" in parts[1]:
                    link, aes_key = parts

            def sync_pdf_dl(actual_link, _pdf_path, _referer, _token=None):
                try:
                    h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'device-id': '39F093FF35F201D9'}
                    if "token=" in actual_link:
                        _t = actual_link.split("token=")[1].split("&")[0]
                        h['x-access-token'] = _t
                        h['api-version'] = "18"
                    elif is_appx:
                        h['Referer'] = _referer
                        h['Origin'] = _referer.rstrip('/')
                    
                    if _token:
                        _clean_token = _token.split('*')[0] if '*' in _token else _token
                        h['Authorization'] = f'Bearer {_clean_token}'
                        h['X-Auth-Token'] = _clean_token
                        h['Cookie'] = f'c_ujwt={_clean_token}; jwt={_clean_token}'
                        h['Referer'] = _referer
                        h['Origin'] = _referer.rstrip('/')
                        
                    _r = cffi_requests.get(actual_link, headers=h, impersonate='chrome', timeout=300)
                    if _r.status_code == 200:
                        with open(_pdf_path, 'wb') as f:
                            f.write(_r.content)
                        return True
                    else:
                        return f"HTTP {_r.status_code}: {_r.content[:100]}"
                except Exception as e:
                    return f"PDF Download Error: {str(e)}"
            success = await asyncio.to_thread(sync_pdf_dl, link, pdf_path, base_url, spayee_token)
            
            if success is not True:
                err_str = success if isinstance(success, str) else "Unknown PDF Download Error"
                await prog_msg.edit_text(f"❌ **Download Failed!**\n`{err_str}`")
                if os.path.exists(pdf_path): os.remove(pdf_path)
                continue

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
            
            # Token & AES Key extraction
            aes_key = None
            spayee_token = None
            is_appx = "appx" in clean_link or "classx" in clean_link or "akamai" in clean_link or "encrypted" in clean_link
            
            if "*" in link:
                star_parts = link.split("*", 1)
                link = star_parts[0]
                if is_appx:
                    aes_key = star_parts[1]
                else:
                    spayee_token = star_parts[1]
            elif ":Zm" in link or ":" in link.split("/")[-1]:
                parts = link.rsplit(":", 1)
                if len(parts) == 2 and len(parts[1]) > 10 and "=" in parts[1]:
                    link, aes_key = parts
            
            # If URL is mkv, download as mkv then convert to mp4 for Telegram
            _raw_path = link.split('?')[0].lower()
            _is_mkv = _raw_path.endswith('.mkv')
            _dl_path = mp4_path.replace('.mp4', '.mkv') if _is_mkv else mp4_path
            success = await download_m3u8(link, _dl_path, base_url, user_id=user_id, spayee_token=spayee_token)
            # Convert mkv to mp4 using ffmpeg (remux, no re-encode - fast)
            if success and _is_mkv and os.path.exists(_dl_path):
                await prog_msg.edit_text(f"⏳ **Converting to MP4...**\n`{name}`")
                try:
                    import subprocess
                    result = await asyncio.to_thread(
                        subprocess.check_output,
                        ["ffmpeg", "-y", "-i", _dl_path, "-c", "copy", mp4_path],
                        stderr=subprocess.STDOUT
                    )
                    if os.path.exists(_dl_path):
                        os.remove(_dl_path)
                except Exception as _ffmpeg_err:
                    print(f"FFmpeg convert error: {_ffmpeg_err}")
                    # Fallback: just rename
                    if os.path.exists(_dl_path):
                        os.rename(_dl_path, mp4_path)
            elif _is_mkv and os.path.exists(_dl_path) and not os.path.exists(mp4_path):
                os.rename(_dl_path, mp4_path)
            
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
                err_str = success if isinstance(success, str) else "Unknown Video Download Error"
                await prog_msg.edit_text(f"❌ **Failed to download Video:**\n`{name}`\n\n**Error Details:**\n`{err_str}`")

    state["is_uploading"] = False
    await message.reply_text(f"✅ **Finished! Successfully processed {uploaded_count} files.**")

@Client.on_message(filters.text & filters.private)
async def handle_text_messages(client: Client, message: Message):
    from bot_state import get_state, clear_state
    user_id = message.from_user.id
    state = get_state(user_id)
    
    if state == "WAITING_FOR_SPAYEE_CREDS":
        text = message.text.strip()
        if " " not in text or "*" not in text:
            await message.reply_text("❌ **Invalid Format!**\nPlease use: `[API_URL] [EMAIL]*[PASSWORD]`")
            return
            
        parts = text.split(" ", 1)
        domain_url = parts[0].strip()
        creds = parts[1].strip()
        email, pwd = creds.split("*", 1)
        
        status_msg = await message.reply_text("⏳ **Authenticating with Ganitank / Spayee...**")
        
        from plugins.extractors.spayee_api import SpayeeClient
        spayee_client = SpayeeClient(domain_url, email, pwd)
        
        # We need an async function to run the sync/async hybrid login
        import asyncio
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        try:
            # Login and fetch courses
            result = await asyncio.wait_for(spayee_client.fetch_courses(), timeout=45)
            
            if not result or not isinstance(result, dict) or not result.get("success"):
                err_msg = result.get("error", "Unknown error") if isinstance(result, dict) else "Authentication Failed"
                await status_msg.edit_text(f"❌ **Login Failed!**\n`{err_msg}`")
                clear_state(user_id)
                return
                
            courses = result.get("courses", [])
            if not courses:
                await status_msg.edit_text("❌ **No enrolled courses found!**")
                clear_state(user_id)
                return
                
            # Keep client in user_tokens for later extraction
            if "spayee_clients" not in globals():
                global spayee_clients
                spayee_clients = {}
            spayee_clients[user_id] = spayee_client
            
            buttons = []
            for c in courses:
                cid = c.get('course_id', c['id'])
                # Telegram callback_data limit is 64 bytes.
                if len(cid) > 40:
                    # In case cid is a full url
                    import re
                    m = re.search(r'([a-f0-9]{24})', cid)
                    if m:
                        cid = m.group(1)
                buttons.append([InlineKeyboardButton(c['title'][:40], callback_data=f"spcourse_{cid}")])
            
            buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="menu_platforms")])
            
            await status_msg.edit_text(
                "✅ **Login Successful!**\n\n**Select a course to extract:**",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            clear_state(user_id)
            
        except Exception as e:
            await status_msg.edit_text(f"❌ **Login Error:**\n`{str(e)}`")
            clear_state(user_id)
