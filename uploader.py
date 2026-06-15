import os
import time
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID_HERE"

DOWNLOAD_DIR = "../extractor/downloads"

class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".mp4"):
            print(f"New video detected: {event.src_path}")
            # Wait a moment to ensure the file is completely written
            time.sleep(5)
            self.upload_video(event.src_path)

    def upload_video(self, filepath):
        if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
            print("Telegram Bot Token is not configured. Skipping upload.")
            return

        print(f"Uploading {filepath} to Telegram...")
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
        
        try:
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if file_size_mb > 50:
                print(f"Warning: File {filepath} is {file_size_mb:.2f}MB. The Telegram standard API limit is 50MB.")
                print("For larger files, you will need to use Pyrogram or a local bot API server.")
                
            with open(filepath, 'rb') as video_file:
                files = {'video': video_file}
                data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': f"Uploaded: {os.path.basename(filepath)}"}
                response = requests.post(url, data=data, files=files)
                
                if response.status_code == 200:
                    print("Successfully uploaded to Telegram.")
                    print(f"Cleaning up local file: {filepath}")
                    os.remove(filepath)
                else:
                    print(f"Failed to upload. Telegram API returned: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error during upload: {e}")

if __name__ == "__main__":
    print(f"Starting Media Sync Service. Monitoring {DOWNLOAD_DIR}...")
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        
    event_handler = VideoHandler()
    observer = Observer()
    observer.schedule(event_handler, path=DOWNLOAD_DIR, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
