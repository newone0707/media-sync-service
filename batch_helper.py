import os
import re
import asyncio
import aiohttp
import shutil
import time
import datetime
import requests as req_lib
from typing import List, Tuple

def decrypt_file(file_path, key):
    import os, mmap
    if not os.path.exists(file_path):
        return False
    with open(file_path, "r+b") as f:
        num_bytes = min(28, os.path.getsize(file_path))
        if num_bytes > 0:
            with mmap.mmap(f.fileno(), length=num_bytes, access=mmap.ACCESS_WRITE) as mmapped_file:
                for i in range(num_bytes):
                    mmapped_file[i] ^= ord(key[i]) if i < len(key) else i
    return True

async def download_direct_file(url: str, out_path: str, referer: str) -> bool:
    import aiohttp
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": referer,
        "Origin": referer.rstrip('/')
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=600)) as resp:
                if resp.status not in [200, 206]:
                    print(f"Direct download failed with status: {resp.status}")
                    return False
                with open(out_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(64 * 1024):
                        f.write(chunk)
        return os.path.isfile(out_path) and os.path.getsize(out_path) > 0
    except Exception as e:
        print(f"Direct download exception: {e}")
        return False

# ─────────────────────────────────────────────
# Appx/Classx direct URL decrypter & resolver
# ─────────────────────────────────────────────
def decrypt_appx_link(enc: str) -> str:
    import base64
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    try:
        enc_data = base64.b64decode(enc.split(':')[0])
        key = '638udh3829162018'.encode('utf-8')
        iv = 'fedcba9876543210'.encode('utf-8')
        if not enc_data:
            return ""
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(enc_data), AES.block_size)
        return plaintext.decode('utf-8')
    except Exception as e:
        print(f"Decryption error: {e}")
        return ""

def resolve_appx_vercel_url(url: str) -> str:
    if "appxsignurl.vercel.app" not in url:
        return url
        
    import urllib.parse
    import requests
    import re
    try:
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        userid = query.get("userid", ["446172"])[0]
        
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 4:
            tenant = path_parts[1]
            course_id = path_parts[2]
            filename = path_parts[3]
            fn_parts = filename.split(".")
            if len(fn_parts) >= 2:
                content_id = fn_parts[-2]
            else:
                return url
        else:
            return url
            
        api_base = f"https://{tenant}api.classx.co.in"
        api_url = f"{api_base}/get/fetchVideoDetailsById?course_id={course_id}&video_id={content_id}&ytflag=0&folder_wise_course=0"
        
        token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6IjQ0NjE3MiIsInRpbWVzdGFtcCI6MTc4MDczMzE4OSwiaXZfdmVyIjoyMywic2Vzc2lvbiI6ImV5SjBlWEFpT2lKS1YxUWlMQ0poYkdjaU9pSklVekkxTmlKOS5leUpwWkNJNklqUTBOakUzTWlJc0ltVnRZV2xzSWpvaWMzVnlZV3ByYUdGeWRXRnlZVUJuYldGcGJDNWpiMjBpTENKdVlXMWxJam9pVTNWeVlXb2dTM1Z0WVhJaUxDSjBaVzVoYm5SVWVYQmxJam9pZFhObGNpSXNJblJsYm1GdWRFNWhiV1VpT2lKcllYVjBhV3g1WVdGc2NHcGxYMlJpSWl3aWRHVnVZVzUwU1dRaU9pSWlMQ0prYVhOd2IzTmhZbXhsSWpwbVlXeHpaWDAuMHdiajdOellzZVNsUTJqQUpfTFFmMDlwMG1lM2NYVmlLWHg2YWZkWmRTdyJ9.Q4BxMCC6y9f14LXvGng8omlkeA5Hc1Jzw7C7exjSJGo"
        
        headers = {
            'Client-Service': 'Appx',
            'Auth-Key': 'appxapi',
            'User-ID': userid,
            'Authorization': token,
            'source': 'website',
            'Host': f"{tenant}api.classx.co.in",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        
        resp = requests.get(api_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            resp_json = resp.json()
            data = resp_json.get("data", {})
            download_link_enc = data.get("download_link") or data.get("pdf_link")
            if download_link_enc:
                decrypted = decrypt_appx_link(download_link_enc)
                if decrypted:
                    return decrypted
    except Exception as e:
        print(f"Error resolving appx URL: {e}")
        
    return url

# Parse batch .txt file
# Supported formats (one per line):
#   Description | URL
#   Description \t URL
#   raw URL only (description auto-generated)
# ─────────────────────────────────────────────
def parse_batch_file(file_path: str) -> List[Tuple[str, str]]:
    entries = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if " : https://" in line:
                desc, url = map(str.strip, line.split(" : https://", 1))
                url = "https://" + url
            elif " : http://" in line:
                desc, url = map(str.strip, line.split(" : http://", 1))
                url = "http://" + url
            elif ":https://" in line:
                desc, url = map(str.strip, line.split(":https://", 1))
                url = "https://" + url
            elif ":http://" in line:
                desc, url = map(str.strip, line.split(":http://", 1))
                url = "http://" + url
            elif "|" in line:
                desc, url = map(str.strip, line.split("|", 1))
            elif "\t" in line:
                desc, url = map(str.strip, line.split("\t", 1))
            else:
                url = line.strip()
                desc = url.split("/")[-1].split("?")[0] or "file"
            entries.append((desc, url.strip()))
    return entries


# ─────────────────────────────────────────────
# Try yt-dlp first (without aria2c for HLS)
# ─────────────────────────────────────────────
async def download_hls_ytdlp(url: str, out_path: str) -> bool:
    """Download m3u8/HLS using yt-dlp native downloader (no aria2c, no ffmpeg merge)."""
    import re
    domain_to_use = "classx.co.in" if "classx" in url else "appx.co.in"
    dyn_origin = "https://appx.co.in"
    tenant_match = re.search(r'/videos/([^-]+)-data/', url)
    if tenant_match:
        tenant = tenant_match.group(1)
        dyn_origin = f"https://{tenant}.{domain_to_use}"

    cmd = [
        "yt-dlp",
        "--no-check-certificate",
        "--hls-use-mpegts",
        "--no-part",
        "-R", "5",
        "--fragment-retries", "10",
        "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "--add-header", f"Origin:{dyn_origin}",
        "--add-header", f"Referer:{dyn_origin}/",
        "-f", "b[height<=720]/best",
        "-o", out_path,
        url,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
    return os.path.isfile(out_path) and os.path.getsize(out_path) > 1024


# ─────────────────────────────────────────────
# Manual m3u8 segment download (fallback)
# Works even if yt-dlp fails - downloads raw TS segments
# ─────────────────────────────────────────────
def download_hls_manual(url: str, out_path: str) -> bool:
    """Fetch m3u8 playlist and download+concatenate all TS segments manually."""
    import re
    domain_to_use = "classx.co.in" if "classx" in url else "appx.co.in"
    dyn_origin = "https://appx.co.in"
    tenant_match = re.search(r'/videos/([^-]+)-data/', url)
    if tenant_match:
        tenant = tenant_match.group(1)
        dyn_origin = f"https://{tenant}.{domain_to_use}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Origin": dyn_origin,
        "Referer": f"{dyn_origin}/",
    }
    try:
        resp = req_lib.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"[HLS] m3u8 fetch failed: HTTP {resp.status_code}")
            return False

        playlist_text = resp.text
        lines = playlist_text.strip().splitlines()

        # If it's a master playlist, pick first variant stream
        if "#EXT-X-STREAM-INF" in playlist_text:
            variant_uri = None
            for i, line in enumerate(lines):
                if line.startswith("#EXT-X-STREAM-INF"):
                    variant_uri = lines[i + 1].strip()
                    break
            if variant_uri:
                if not variant_uri.startswith("http"):
                    base = url.rsplit("/", 1)[0] + "/"
                    variant_uri = base + variant_uri
                resp2 = req_lib.get(variant_uri, headers=headers, timeout=30)
                if resp2.status_code != 200:
                    return False
                playlist_text = resp2.text
                lines = playlist_text.strip().splitlines()
                base_url = variant_uri.rsplit("/", 1)[0] + "/"
            else:
                base_url = url.rsplit("/", 1)[0] + "/"
        else:
            base_url = url.rsplit("/", 1)[0] + "/"

        # Collect segment URIs
        segments = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                seg_url = line if line.startswith("http") else base_url + line
                segments.append(seg_url)

        if not segments:
            print("[HLS] No segments found in playlist")
            return False

        print(f"[HLS] Downloading {len(segments)} segments...")
        with open(out_path, "wb") as out_f:
            for i, seg_url in enumerate(segments):
                for attempt in range(3):
                    try:
                        seg_resp = req_lib.get(seg_url, headers=headers, timeout=60)
                        if seg_resp.status_code == 200:
                            out_f.write(seg_resp.content)
                            break
                    except Exception as e:
                        if attempt == 2:
                            print(f"[HLS] Segment {i} failed: {e}")
                        time.sleep(1)

        return os.path.isfile(out_path) and os.path.getsize(out_path) > 1024

    except Exception as e:
        print(f"[HLS] Manual download exception: {e}")
        return False


# ─────────────────────────────────────────────
# Combined HLS downloader: yt-dlp → manual fallback
# ─────────────────────────────────────────────
async def download_hls(url: str, out_path: str) -> bool:
    print(f"[HLS] Trying yt-dlp for: {url[:80]}")
    try:
        ok = await download_hls_ytdlp(url, out_path)
        if ok:
            return True
    except Exception as e:
        print(f"[HLS] yt-dlp failed: {e}")

    print("[HLS] Falling back to manual segment download...")
    return download_hls_manual(url, out_path)


# ─────────────────────────────────────────────
# Generic download (PDF / image)
# ─────────────────────────────────────────────
async def download_file(url: str, out_path: str) -> bool:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    return False
                with open(out_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(64 * 1024):
                        f.write(chunk)
        return os.path.isfile(out_path) and os.path.getsize(out_path) > 0
    except Exception:
        return False


# ─────────────────────────────────────────────
# Spayee PDF download helper
# ─────────────────────────────────────────────
async def download_spayee_pdf(url: str, out_path: str, token: str) -> bool:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Authorization": f"Bearer {token}",
        "Cookie": f"c_ujwt={token}; jwt={token}",
        "Referer": "https://www.rglectures.com/",
        "Origin": "https://www.rglectures.com"
    }
    
    def fetch_pdf():
        from curl_cffi import requests as cffi_requests
        print(f"[Spayee PDF] Fetching: {url[:80]}...")
        r = cffi_requests.get(url, headers=headers, impersonate='chrome', timeout=300)
        return r.status_code, r.content
        
    try:
        loop = asyncio.get_event_loop()
        status_code, content = await loop.run_in_executor(None, fetch_pdf)
        if status_code != 200:
            print(f"[Spayee PDF] Download failed: HTTP {status_code}")
            return False
        with open(out_path, "wb") as f:
            f.write(content)
        return os.path.isfile(out_path) and os.path.getsize(out_path) > 0
    except Exception as e:
        print(f"[Spayee PDF] Exception: {e}")
        return False


# ─────────────────────────────────────────────
# Spayee Video download helper (HLS Decryption)
# ─────────────────────────────────────────────
async def download_spayee_video(url: str, out_path: str, token: str, spayee_key_b64: str = None) -> bool:
    import base64
    import json
    import urllib.parse
    from Crypto.Cipher import AES
    import yt_dlp
    from yt_dlp.networking.impersonate import ImpersonateTarget

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Authorization": f"Bearer {token}",
        "Cookie": f"c_ujwt={token}; jwt={token}",
        "Referer": "https://www.rglectures.com/",
        "Origin": "https://www.rglectures.com"
    }

    def curl_get(fetch_url):
        from curl_cffi import requests as cffi_requests
        r = cffi_requests.get(fetch_url, headers=headers, impersonate='chrome', timeout=30)
        return r.status_code, r.content

    try:
        loop = asyncio.get_event_loop()

        # 1. Fetch Master Playlist
        print(f"[Spayee Video] Fetching master: {url[:80]}")
        status, content = await loop.run_in_executor(None, curl_get, url)
        if status != 200:
            print(f"[Spayee Video] Failed to fetch master: HTTP {status}")
            return False
        master_text = content.decode("utf-8", errors="ignore")

        base_url_hls = url.split("?")[0].rsplit("/", 1)[0] + "/"

        # 2. Extract best variant playlist
        max_bw = 0
        best_res_url = None
        lines = master_text.splitlines()
        for j, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                bw_match = re.search(r"BANDWIDTH=(\d+)", line)
                bw = int(bw_match.group(1)) if bw_match else 0
                if bw >= max_bw:
                    max_bw = bw
                    best_res_url = lines[j+1].strip()

        if best_res_url:
            if not best_res_url.startswith("http"):
                best_res_url = urllib.parse.urljoin(base_url_hls, best_res_url)
            print(f"[Spayee Video] Fetching sub playlist: {best_res_url[:80]}")
            status, content = await loop.run_in_executor(None, curl_get, best_res_url)
            if status != 200:
                print(f"[Spayee Video] Failed to fetch sub playlist: HTTP {status}")
                return False
            sub_text = content.decode("utf-8", errors="ignore")
            base_url_hls = best_res_url.split("?")[0].rsplit("/", 1)[0] + "/"
        else:
            sub_text = master_text

        # 3. Download the first segment to check decryption sync byte
        first_ts_url = None
        iv_hex = None
        for line in sub_text.splitlines():
            if line.startswith("#EXT-X-KEY"):
                iv_match = re.search(r"IV=0x([0-9a-fA-F]+)", line)
                if iv_match:
                    iv_hex = iv_match.group(1)
            elif line and not line.startswith("#"):
                first_ts_url = urllib.parse.urljoin(base_url_hls, line) if not line.startswith("http") else line
                break

        iv = bytes.fromhex(iv_hex) if iv_hex else b"\x00" * 16
        first_ts_blob = None
        if first_ts_url:
            print(f"[Spayee Video] Fetching first TS segment for sync verification...")
            status, content = await loop.run_in_executor(None, curl_get, first_ts_url)
            if status == 200:
                first_ts_blob = content[:1024]

        def check_aes(k):
            if not first_ts_blob or len(first_ts_blob) < 944:
                return False
            try:
                c = AES.new(k, AES.MODE_CBC, iv=iv)
                d = c.decrypt(first_ts_blob[:944])
                if len(d) >= 940 and d[0] == 0x47 and d[188] == 0x47 and d[376] == 0x47 and d[564] == 0x47 and d[752] == 0x47:
                    return True
            except:
                pass
            return False

        # Decode JWT claims p & e for XOR derivation
        payload_b64 = token.split(".")[1]
        pad = len(payload_b64) % 4
        if pad:
            payload_b64 += "=" * (4 - pad)
        payload = json.loads(base64.b64decode(payload_b64).decode())

        def safe_b64decode(s):
            pad = len(s) % 4
            if pad:
                s += "=" * (4 - pad)
            return base64.b64decode(s)

        p_bytes = safe_b64decode(payload.get("p", ""))
        e_bytes = safe_b64decode(payload.get("e", ""))

        # 4. Parse Sub Playlist lines and process key
        new_lines = []
        local_key_path = out_path + ".key"
        local_m3u8 = out_path + ".m3u8"

        for line in sub_text.splitlines():
            if line.startswith("#EXT-X-KEY"):
                uri_match = re.search(r'URI="([^"]+)"', line)
                if uri_match:
                    uri = uri_match.group(1)
                    abs_uri = urllib.parse.urljoin(base_url_hls, uri) if not uri.startswith("http") else uri
                    
                    key_blob = None
                    if spayee_key_b64:
                        try:
                            key_blob = base64.b64decode(spayee_key_b64)
                            print("[Spayee Video] Using pre-extracted key blob from URL suffix")
                        except Exception as e:
                            print(f"[Spayee Video] Failed to decode key blob suffix: {e}")
                    
                    if not key_blob:
                        print(f"[Spayee Video] Fetching key blob from: {abs_uri[:80]}")
                        status, content = await loop.run_in_executor(None, curl_get, abs_uri)
                        if status != 200:
                            print(f"[Spayee Video] Failed to fetch key blob: HTTP {status}")
                            return False
                        key_blob = content
                    
                    decrypted_key = None

                    # Try Plain Slices/Offsets
                    for offset in range(len(key_blob) - 15):
                        k = key_blob[offset:offset+16]
                        if check_aes(k):
                            decrypted_key = k
                            print(f"[Spayee Video] Decrypted key match at plain offset: {offset}")
                            break

                    # Try Token XOR
                    if not decrypted_key:
                        t_bytes = token.encode()
                        for k_off in range(len(key_blob) - 15):
                            if decrypted_key:
                                break
                            for t_off in range(len(t_bytes) - 15):
                                k = bytes([a ^ b for a, b in zip(key_blob[k_off:k_off+16], t_bytes[t_off:t_off+16])])
                                if check_aes(k):
                                    decrypted_key = k
                                    print(f"[Spayee Video] Decrypted key match at Token XOR: k={k_off}, t={t_off}")
                                    break

                    # Try p XOR e XOR key_blob 3-part XOR
                    if not decrypted_key and p_bytes and e_bytes:
                        for k_off in range(len(key_blob) - 15):
                            if decrypted_key:
                                break
                            for p_off in range(len(p_bytes) - 15):
                                if decrypted_key:
                                    break
                                for e_off in range(len(e_bytes) - 15):
                                    pe = bytes([a ^ b for a, b in zip(p_bytes[p_off:p_off+16], e_bytes[e_off:e_off+16])])
                                    k = bytes([a ^ b for a, b in zip(key_blob[k_off:k_off+16], pe)])
                                    if check_aes(k):
                                        decrypted_key = k
                                        print(f"[Spayee Video] Decrypted key match at 3-part XOR: k={k_off}, p={p_off}, e={e_off}")
                                        break

                    if decrypted_key:
                        with open(local_key_path, "wb") as kf:
                            kf.write(decrypted_key)
                        # Update key path in manifest to absolute file URL
                        local_key_url = "file:///" + os.path.abspath(local_key_path).replace("\\", "/")
                        line = line.replace(f'URI="{uri}"', f'URI="{local_key_url}"')
                    else:
                        print("[Spayee Video] WARNING: Decryption brute-force failed. Using remote key.")
                        line = line.replace(f'URI="{uri}"', f'URI="{abs_uri}"')

                new_lines.append(line)
            elif line and not line.startswith("#"):
                abs_ts = urllib.parse.urljoin(base_url_hls, line) if not line.startswith("http") else line
                new_lines.append(abs_ts)
            else:
                new_lines.append(line)

        # Write temporary local playlist
        with open(local_m3u8, "w", encoding="utf-8") as lf:
            lf.write("\n".join(new_lines))

        # 5. Download HLS stream using yt-dlp subprocess
        # On Windows, local file paths must be converted to a valid file URL: file:///C:/path/to/local.m3u8
        local_m3u8_abs = os.path.abspath(local_m3u8)
        local_m3u8_url = "file:///" + local_m3u8_abs.replace("\\", "/")

        ydl_opts = {
            "format": "best",
            "outtmpl": out_path,
            "quiet": True,
            "no_warnings": True,
            "http_headers": headers,
            "enable_file_urls": True,
            "impersonate": ImpersonateTarget(client="chrome"),
            "concurrent_fragment_downloads": 10
        }
        print(f"[Spayee Video] Starting yt-dlp on: {local_m3u8_url}")
        
        # We must run yt-dlp inside asyncio threadpool executor since it's blocking
        def run_ytdl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.download([str(local_m3u8_url)])
                
        ret = await loop.run_in_executor(None, run_ytdl)

        # Cleanup temp files
        #     os.remove(local_m3u8)
        # if os.path.exists(local_key_path):
        #     os.remove(local_key_path)

        return ret == 0
    except Exception as e:
        print(f"[Spayee Video] Download failed: {e}")
        # Cleanup
        if "local_m3u8" in locals() and os.path.exists(local_m3u8):
            os.remove(local_m3u8)
        if "local_key_path" in locals() and os.path.exists(local_key_path):
            os.remove(local_key_path)
        return False


# ─────────────────────────────────────────────
# Caption generator
# ─────────────────────────────────────────────
def generate_caption(idx: int, desc: str, url: str, credit_name: str,
                     topic_name: str = "", batch_name: str = "") -> str:
    vid_id_match = re.search(r"[?&]id=(\d+)", url)
    vid_id = vid_id_match.group(1) if vid_id_match else str(idx).zfill(3)
    is_pdf = ".pdf" in url.lower()
    icon = "📑" if is_pdf else "🎥"
    ext = ".pdf" if is_pdf else ".mp4"
    title = f"{desc}{ext}"
    topic = topic_name or desc
    batch = batch_name or "Batch"
    return (
        f"[{icon}]Vid Id : {vid_id}\n"
        f"Video Title : {title}\n"
        f"Topic Name : {topic}\n"
        f"Batch Name : {batch}\n\n"
        f"Downloadd By ➤ {credit_name}"
    )


# ─────────────────────────────────────────────
# Main batch processor
# ─────────────────────────────────────────────
async def process_batch(
    txt_path: str,
    bot,
    chat_id: int,
    user_id: int,
    credit_name: str = "{CREDIT}",
    batch_name: str = "Batch",
    cptoken_from_main: str = "",
):
    base_dir = os.path.dirname(txt_path) or "."
    temp_dir = os.path.join(base_dir, f"temp_{chat_id}")
    os.makedirs(temp_dir, exist_ok=True)

    entries = parse_batch_file(txt_path)
    total = len(entries)
    
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    try:
        cptoken_from_file = content.split("cptoken=")[1].split("\n")[0].strip()
    except:
        cptoken_from_file = None
        
    raw_base_url = "https://web.classplusapp.com"
    for line in content.splitlines():
        if line.strip().startswith("BaseURL:"):
            raw_base_url = line.split("BaseURL:")[1].strip()
            break
            
    import re as _re
    _m = _re.match(r'(https?://)([^.]+?)(api)?\.(.+)$', raw_base_url, _re.IGNORECASE)
    if _m:
        base_url = f"{_m.group(1)}{_m.group(2)}.{_m.group(4)}/"
    else:
        base_url = raw_base_url.rstrip('/') + '/'
        
    await bot.send_message(chat_id, f"📋 <b>Batch started</b> – {total} items found. Processing…")

    success_cnt = 0
    fail_cnt = 0
    index_lines = []

    for idx, (desc, url) in enumerate(entries, start=1):
        url = resolve_appx_vercel_url(url)
        
        spayee_token = None
        spayee_key_b64 = None
        is_spayee = False
        if ("spayee.in" in url or "cloudfront.net" in url) and "*" in url:
            is_spayee = True
            parts = url.split("*")
            url = parts[0]
            spayee_token = parts[1]
            if len(parts) >= 3:
                spayee_key_b64 = parts[2]

        aes_key = None
        if not is_spayee and "*" in url:
            parts = url.split("*", 1)
            url = parts[0]
            aes_key = parts[1]
            
        _path_lower = url.split("?")[0].lower()
        is_encrypted_video = not is_spayee and ("encrypted.mkv" in _path_lower or "encrypted.mp4" in _path_lower or ".zip" in _path_lower or "static-trans" in url or "static-db" in url or aes_key is not None)
        
        if "classplusapp" in url and "Signature=" not in url:
            try:
                cptoken = cptoken_from_file or cptoken_from_main
                if cptoken and cptoken != "cptoken":
                    url = url.replace("https://cpvod.testbook.com/","https://media-cdn.classplusapp.com/drm/")
                    import requests
                    if "contentId=" in url:
                        cid = url.split("contentId=")[1].split("&")[0]
                        res = requests.get("https://api.classplusapp.com/cams/uploader/video/jw-signed-url", params={"contentId": cid, "offlineDownload": "false"}, headers={"x-access-token": cptoken, "host": "api.classplusapp.com", "app-version": "1.4.73.2", "device-id": "c28d3cb16bbdac01", "user-agent": "Mobile-Android"}).json()
                        if "url" in res: url = res["url"]
                        elif "drmUrls" in res: url = res["drmUrls"]["manifestUrl"]
                    else:
                        res = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers={'x-access-token': f'{cptoken}'}).json()
                        if "url" in res: url = res["url"]
            except Exception as e:
                print(f"Classplus batch API failed: {e}")
                
        safe_desc = re.sub(r'[\\/*?:"<>|]', "", desc)[:80].strip()
        safe_desc = safe_desc.replace(" ", "_") or f"file_{idx}"

        progress_msg = await bot.send_message(
            chat_id,
            f"⏬ <b>[{idx}/{total}]</b> Downloading…\n<code>{desc[:80]}</code>"
        )

        try:
            # ── Encrypted/Direct Video or File ───────
            if is_encrypted_video:
                _is_mkv = _path_lower.endswith(".mkv") or "encrypted.mkv" in _path_lower
                _dl_path = os.path.join(temp_dir, f"{safe_desc}.mkv") if _is_mkv else os.path.join(temp_dir, f"{safe_desc}.mp4")
                out_file = os.path.join(temp_dir, f"{safe_desc}.mp4")
                
                ok = await download_direct_file(url, _dl_path, base_url)
                if ok:
                    if _is_mkv and os.path.exists(_dl_path):
                        await progress_msg.edit(f"⏳ <b>Converting to MP4...</b>\n<code>{desc}</code>")
                        try:
                            import subprocess
                            subprocess.run(f'ffmpeg -y -i "{_dl_path}" -c copy "{out_file}"', shell=True, check=True)
                            if os.path.exists(_dl_path):
                                os.remove(_dl_path)
                        except Exception as _ffmpeg_err:
                            print(f"FFmpeg convert error: {_ffmpeg_err}")
                            if os.path.exists(_dl_path) and not os.path.exists(out_file):
                                os.rename(_dl_path, out_file)
                                
                    if aes_key and os.path.exists(out_file):
                        await progress_msg.edit(f"⏳ <b>Decrypting Video...</b>\n<code>{desc}</code>")
                        decrypt_file(out_file, aes_key)
                        
                    cap = generate_caption(idx, desc, url, credit_name, desc, batch_name)
                    
                    thumb_path = f"{out_file}.jpg"
                    try:
                        import subprocess
                        subprocess.run(f'ffmpeg -y -i "{out_file}" -ss 00:00:02 -vframes 1 "{thumb_path}"', shell=True)
                        if not os.path.exists(thumb_path):
                            thumb_path = None
                    except:
                        thumb_path = None
                        
                    dur = 0
                    try:
                        from saini import duration
                        dur = int(duration(out_file))
                    except:
                        pass
                        
                    await bot.send_video(
                        chat_id=chat_id,
                        video=out_file,
                        caption=cap,
                        supports_streaming=True,
                        thumb=thumb_path,
                        duration=dur,
                        width=1280,
                        height=720,
                    )
                    success_cnt += 1
                    index_lines.append(f"{str(idx).zfill(2)}. {desc}")
                else:
                    fail_cnt += 1
                    await bot.send_message(
                        chat_id,
                        f"⚠️ <b>Downloading Failed</b>\n"
                        f"Name =&gt;&gt; <code>{desc}</code>\n"
                        f"Failed Reason: Direct download failed.",
                        disable_web_page_preview=True,
                    )

            # ── HLS / video ─────────────────────────
            elif "m3u8" in url.lower():
                out_file = os.path.join(temp_dir, f"{safe_desc}.mp4")
                if is_spayee:
                    ok = await download_spayee_video(url, out_file, spayee_token, spayee_key_b64)
                else:
                    ok = await download_hls(url, out_file)
                if ok:
                    cap = generate_caption(idx, desc, url, credit_name, desc, batch_name)
                    
                    import subprocess
                    thumb_path = f"{out_file}.jpg"
                    subprocess.run(f'ffmpeg -y -i "{out_file}" -ss 00:00:01 -vframes 1 "{thumb_path}"', shell=True)
                    if not os.path.exists(thumb_path):
                        thumb_path = None
                        
                    dur = 0
                    try:
                        from saini import duration
                        dur = int(duration(out_file))
                    except:
                        pass
                        
                    await bot.send_video(
                        chat_id=chat_id,
                        video=out_file,
                        caption=cap,
                        supports_streaming=True,
                        thumb=thumb_path,
                        duration=dur,
                        width=1280,
                        height=720,
                    )
                    success_cnt += 1
                    index_lines.append(f"{str(idx).zfill(2)}. {desc}")
                else:
                    fail_cnt += 1
                    await bot.send_message(
                        chat_id,
                        f"⚠️ <b>Downloading Failed</b>\n"
                        f"Name =&gt;&gt; <code>{desc}</code>\n"
                        f"Url =&gt;&gt; <code>{url}</code>\n\n"
                        f"Failed Reason: Both yt-dlp and manual segment download failed.",
                        disable_web_page_preview=True,
                    )

            # ── PDF ─────────────────────────────────
            elif ".pdf" in url.lower():
                out_file = os.path.join(temp_dir, f"{safe_desc}.pdf")
                if is_spayee:
                    ok = await download_spayee_pdf(url, out_file, spayee_token)
                else:
                    ok = await download_file(url, out_file)
                if ok:
                    cap = generate_caption(idx, desc, url, credit_name, desc, batch_name)
                    await bot.send_document(chat_id=chat_id, document=out_file, caption=cap)
                    success_cnt += 1
                    index_lines.append(f"{str(idx).zfill(2)}. {desc}")
                else:
                    fail_cnt += 1
                    await bot.send_message(
                        chat_id,
                        f"⚠️ <b>Downloading Failed</b>\n"
                        f"Name =&gt;&gt; <code>{desc}</code>\n"
                        f"Failed Reason: PDF returned non-200.",
                        disable_web_page_preview=True,
                    )

            # ── Image ────────────────────────────────
            elif any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png"]):
                ext_i = url.lower().rsplit(".", 1)[-1].split("?")[0]
                out_file = os.path.join(temp_dir, f"{safe_desc}.{ext_i}")
                ok = await download_file(url, out_file)
                if ok:
                    cap = generate_caption(idx, desc, url, credit_name, desc, batch_name)
                    await bot.send_photo(chat_id=chat_id, photo=out_file, caption=cap)
                    success_cnt += 1
                    index_lines.append(f"{str(idx).zfill(2)}. {desc}")
                else:
                    fail_cnt += 1
                    await bot.send_message(chat_id, f"⚠️ Failed image: <code>{desc}</code>")

            # ── Other / fallback ─────────────────────
            else:
                out_file = os.path.join(temp_dir, f"{safe_desc}.mp4")
                ok = await download_hls_ytdlp(url, out_file)
                if ok:
                    cap = generate_caption(idx, desc, url, credit_name, desc, batch_name)
                    await bot.send_video(
                        chat_id=chat_id, video=out_file,
                        caption=cap, supports_streaming=True
                    )
                    success_cnt += 1
                    index_lines.append(f"{str(idx).zfill(2)}. {desc}")
                else:
                    fail_cnt += 1
                    await bot.send_message(
                        chat_id,
                        f"⚠️ <b>Downloading Failed</b>\n<code>{desc}</code>",
                        disable_web_page_preview=True,
                    )

        except Exception as e:
            fail_cnt += 1
            await bot.send_message(
                chat_id,
                f"⚠️ <b>Error</b>\nName =&gt;&gt; <code>{desc}</code>\nReason: <code>{str(e)[:200]}</code>",
            )

        finally:
            try:
                await progress_msg.delete()
            except Exception:
                pass
            # cleanup temp files for this item
            for p in os.listdir(temp_dir):
                try:
                    os.remove(os.path.join(temp_dir, p))
                except Exception:
                    pass

    # ── Summary ─────────────────────────────────
    await bot.send_message(
        chat_id,
        f"✅ <b>Batch Complete!</b>\n\n"
        f"• Total  : {total}\n"
        f"• Success: {success_cnt}\n"
        f"• Failed : {fail_cnt}",
    )

    # ── Index (WhatsApp style) ───────────────────
    if index_lines:
        ts = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        index_header = f"[{ts}] 𝓐𝓭𝓲𝓽𝔂𝓪: 📑 Topics covered in this Batch:\n\n"
        index_body = "\n".join(index_lines)
        full_index = index_header + index_body
        for chunk_start in range(0, len(full_index), 4000):
            await bot.send_message(chat_id, full_index[chunk_start:chunk_start + 4000])

    # ── Cleanup ──────────────────────────────────
    shutil.rmtree(temp_dir, ignore_errors=True)
    try:
        os.remove(txt_path)
    except Exception:
        pass
