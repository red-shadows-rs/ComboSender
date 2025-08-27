import os
import asyncio
import importlib.util
import telegram
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
)
from src.session.telethon_session import telethon_client, telethon_login
from src.data.database import conn, c
from src.bot.handlers import (
    start,
    add_input_channel,
    save_input_channel,
    add_output_channel,
    save_output_channel,
    save_rights_emails,
    handle_document,
    callback_query_handler,
    setup_telethon_handlers,
)
from config import TELEGRAM_BOT_TOKEN

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

ADD_INPUT, ADD_OUTPUT = range(2)

app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("add_input", add_input_channel),
        CommandHandler("add_output", add_output_channel),
        CallbackQueryHandler(add_input_channel, pattern="^add_input$"),
        CallbackQueryHandler(add_output_channel, pattern="^add_output$"),
    ],
    states={
        ADD_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_input_channel)
        ],
        ADD_OUTPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_output_channel)
        ],
        "RIGHTS_EMAILS": [
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_rights_emails)
        ],
    },
    fallbacks=[],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.add_handler(CallbackQueryHandler(callback_query_handler))


async def main():
    await telethon_login()
    setup_telethon_handlers()
    asyncio.create_task(telethon_client.run_until_disconnected())
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()
    await app.stop()
    await app.shutdown()


if __name__ == "__main__":
    missing = []
    for pkg in ["telethon"]:
        if importlib.util.find_spec(pkg) is None:
            missing.append(pkg)
    if missing:
        print(
            f"\n⚠️ Required packages are missing: {', '.join(missing)}\nPlease run: pip install -r requirements.txt\n"
        )
    print(
        """
🤖 ComboSender Dashboard Bot
───────────────────────
Team: RED SHADOWS | RS
Developer: Shadow_x78
GitHub: https://github.com/red-shadows-rs
───────────────────────

Bot is starting...
"""
    )
    asyncio.run(main())
