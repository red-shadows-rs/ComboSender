import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
APP_ID = int(os.getenv("APP_ID"))
APP_HASH = os.getenv("APP_HASH")
ADMIN_IDS = eval(os.getenv("ADMIN_IDS"))
