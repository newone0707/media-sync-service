import os
import threading
import requests
from flask import Flask, request, jsonify
import yt_dlp
import uuid

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
DOWNLOAD_DIR = "downloads"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def upload_to_telegram(chat_id, filepath, title):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    print(f"Uploading {filepath} to Telegram...")
    try:
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if file_size_mb > 50:
            send_telegram_message(chat_id, f"⚠️ Warning: '{title}' is {file_size_mb:.2f}MB. Standard Telegram bots limit is 50MB. Upload might fail.")
            
        with open(filepath, 'rb') as doc:
            files = {'document': (os.path.basename(filepath), doc)}
            data = {'chat_id': chat_id, 'caption': title}
            response = requests.post(url, data=data, files=files)
            
            if response.status_code == 200:
                print("Successfully uploaded to Telegram.")
                send_telegram_message(chat_id, f"✅ Successfully uploaded: {title}")
            else:
                print(f"Failed to upload. Status: {response.status_code} - {response.text}")
                send_telegram_message(chat_id, f"❌ Failed to upload: {title}. Size limit or API error.")
    except Exception as e:
        print(f"Error during upload: {e}")
        send_telegram_message(chat_id, f"❌ Error uploading {title}: {e}")
    finally:
        # Cleanup
        if os.path.exists(filepath):
            os.remove(filepath)

def process_download(title, url, chat_id):
    send_telegram_message(chat_id, f"⬇️ Starting download: {title}")
    
    # Generate unique filename based on title or uuid to avoid conflicts
    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    if not safe_title:
        safe_title = str(uuid.uuid4())[:8]
    
    if ".m3u8" in url:
        output_filename = os.path.join(DOWNLOAD_DIR, f"{safe_title}.mp4")
        ydl_opts = {
            'outtmpl': output_filename,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4'
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            upload_to_telegram(chat_id, output_filename, title)
        except Exception as e:
            print(f"Download failed: {e}")
            send_telegram_message(chat_id, f"❌ Download failed for {title}: {e}")
    else:
        # Direct download for pdf, jpg, etc.
        ext = url.split("?")[0].split("*")[0].split(".")[-1]
        if len(ext) > 4: ext = "file" # fallback
        output_filename = os.path.join(DOWNLOAD_DIR, f"{safe_title}.{ext}")
        
        try:
            # We must handle the URL correctly, removing the `*` suffix if it breaks standard download
            # Some Spayee URLs have `*uuid` at the end
            clean_url = url.split('*')[0]
            resp = requests.get(clean_url, stream=True)
            resp.raise_for_status()
            with open(output_filename, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            upload_to_telegram(chat_id, output_filename, title)
        except Exception as e:
            print(f"Download failed: {e}")
            send_telegram_message(chat_id, f"❌ Direct download failed for {title}: {e}")

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    if not data or 'url' not in data or 'title' not in data or 'chat_id' not in data:
        return jsonify({"error": "Missing url, title, or chat_id"}), 400
        
    title = data['title']
    url = data['url']
    chat_id = data['chat_id']
    
    # Start background thread so we don't block the Flask response
    thread = threading.Thread(target=process_download, args=(title, url, chat_id))
    thread.start()
    
    return jsonify({"status": "processing", "title": title}), 200

@app.route('/', methods=['GET'])
def health():
    return "Media Sync Service is running!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
