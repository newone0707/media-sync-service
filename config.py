import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API credentials from my.telegram.org
API_ID = int(os.environ.get("API_ID", "1234567"))
API_HASH = os.environ.get("API_HASH", "your_api_hash_here")

# Bot Token from @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "8762166731:AAEUa-CEhKRLsfWGDdSk4Gau_ujJbMHgcFs")

# Owner ID and Authorized Users
OWNER_ID = int(os.environ.get("OWNER_ID", "123456789"))

# Authorized users stored in memory (in a real app, use a database)
AUTH_USERS = [OWNER_ID]
