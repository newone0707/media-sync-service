import os
import threading
from pyrogram import Client
from flask import Flask
from config import API_ID, API_HASH, BOT_TOKEN

# Initialize Flask App for Render Free Tier Dummy Server
app = Flask(__name__)

@app.route("/")
def index():
    return "Pyrogram Bot is Running ✅"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Please set the TELEGRAM_BOT_TOKEN environment variable.")
        exit(1)

    # Start dummy web server in the background
    threading.Thread(target=run_web, daemon=True).start()

    # Initialize and start the Pyrogram Client
    print("Starting Pyrogram Bot...")
    bot = Client(
        "leach_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        ipv6=False,
        plugins=dict(root="plugins")
    )
    bot.run()
