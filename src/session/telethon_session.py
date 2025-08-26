from telethon import TelegramClient
from config import APP_ID, APP_HASH

SESSION_NAME = "src/session/combo_sender.session"

try:
    telethon_client = TelegramClient(SESSION_NAME, APP_ID, APP_HASH)
except ImportError:
    print("Telethon is not installed. Please run: pip install telethon")


def telethon_login():
    return telethon_client.start()
