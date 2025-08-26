import os
import asyncio
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
from src.session.telethon_session import telethon_client, telethon_login
from src.bot.handlers import (
    start,
    ask_input_channel,
    save_input_channel,
    ask_output_channel,
    save_output_channel,
    save_rights_emails,
    channels_menu,
    delete_channel,
    skip_rights_handler,
    STATE,
    CALLBACK,
)
from config import TELEGRAM_BOT_TOKEN


def main():
    if not os.path.exists("temp"):
        os.makedirs("temp")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ask_input_channel, pattern=f"^{CALLBACK.ADD_INPUT}$"),
            CallbackQueryHandler(
                ask_output_channel, pattern=f"^{CALLBACK.ADD_OUTPUT}$"
            ),
        ],
        states={
            STATE.ADD_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_input_channel)
            ],
            STATE.ADD_OUTPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_output_channel)
            ],
            STATE.ADD_RIGHTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_rights_emails),
                CallbackQueryHandler(
                    skip_rights_handler, pattern=f"^{CALLBACK.SKIP_RIGHTS}$"
                ),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(channels_menu, pattern=f"^{CALLBACK.CHANNELS}$")
        ],
        per_message=False,
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))

    application.add_handler(
        CallbackQueryHandler(start, pattern=f"^{CALLBACK.BACK_TO_MAIN}$")
    )
    application.add_handler(
        CallbackQueryHandler(channels_menu, pattern=f"^{CALLBACK.CHANNELS}$")
    )
    application.add_handler(
        CallbackQueryHandler(delete_channel, pattern=f"^{CALLBACK.DELETE_INPUT_PREFIX}")
    )
    application.add_handler(
        CallbackQueryHandler(
            delete_channel, pattern=f"^{CALLBACK.DELETE_OUTPUT_PREFIX}"
        )
    )

    async def run_bot():
        await telethon_login()

        async with application:
            await application.initialize()
            await application.start()

            asyncio.create_task(telethon_client.run_until_disconnected())

            await application.updater.start_polling()
            print("🤖 Bot is running and listening for updates...")
            await asyncio.Event().wait()

            await application.updater.stop()
            await application.stop()
            await application.shutdown()

    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")


if __name__ == "__main__":
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
    main()
