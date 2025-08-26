# 🤖 ComboSender Bot

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)
![Telethon](https://img.shields.io/badge/Telethon-API-blue?logo=telegram)
![Asyncio](https://img.shields.io/badge/Asyncio-Enabled-blue?logo=python)

---

## 📦 Project Description

ComboSender Bot for managing and sending combo files between Telegram channels using Telethon and python-telegram-bot. Features combo filtering, dynamic channel management, rights emails insertion, detailed logging, and automatic temp file cleanup.

---

## 🚀 Features

- Receive combo files from specified Telegram channels.
- Send filtered combo files to output channels.
- Automatically insert rights emails into sent files.
- Dynamically update Telethon event listeners when channels are added/removed.
- Detailed logging for line count, emails, and filtered combos.
- Automatic deletion of temp files after processing.
- Access protection via admin IDs.
- Handles asyncio exceptions to hide error messages on shutdown.

---

## 🛠️ Requirements

- Python 3.11+
- Telethon
- python-telegram-bot
- All dependencies in `requirements.txt`

---

## ⚡ Usage

```bash
pip install -r requirements.txt
python main.py
```

---

## 📚 Main Files

- `main.py`: Bot entry point and event management.
- `src/bot/handlers.py`: Channel management, file handling, filtering, logging.
- `src/session/telethon_session.py`: Telethon session setup.
- `src/data/database.py`: Database management.
- `src/utils/checker.py`: Combo filtering and validation functions.
- `config.py`: Bot configuration and admin IDs.

---

## 📝 Notes

- Add your admin IDs in `config.py`.
- Only registered input channels can send files to the bot.
- Files are sent only if the filtered combo count is greater than 100.

---

## 📜 License

MIT — see [LICENSE](LICENSE)

---

© 2025 Copyright

![RED SHADOWS | RS](https://img.shields.io/badge/RED%20SHADOWS%20%7C%20RS-DC143C?style=flat&logo=github&logoColor=white&labelColor=2F2F2F) | ![Shadow-x78](https://img.shields.io/badge/Shadow--x78-000000?style=flat&logo=github&logoColor=white&labelColor=2F2F2F) — **All rights reserved**
