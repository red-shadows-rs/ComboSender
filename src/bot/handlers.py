from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
)
from telethon import events
import os
import re
from src.data.database import c, conn
from src.utils.checker import checker_combo
from src.session.telethon_session import telethon_client
from config import ADMIN_IDS

ADD_INPUT, ADD_OUTPUT = range(2)
TEMP_DIR = "temp"

input_channels = set(
    row[0] for row in c.execute("SELECT channel_id FROM input_channels")
)
output_channels = [
    (row[0], row[1])
    for row in c.execute("SELECT channel_id, file_name FROM output_channels")
]


def is_admin(update):
    user_id = None
    if hasattr(update, "effective_user") and update.effective_user:
        user_id = update.effective_user.id
    elif hasattr(update, "message") and update.message and update.message.from_user:
        user_id = update.message.from_user.id
    elif (
        hasattr(update, "callback_query")
        and update.callback_query
        and update.callback_query.from_user
    ):
        user_id = update.callback_query.from_user.id
    return user_id in ADMIN_IDS


async def start(update: Update, context: CallbackContext):
    if not is_admin(update):
        message = getattr(update, "message", None)
        if (
            message is None
            and hasattr(update, "callback_query")
            and update.callback_query
        ):
            message = update.callback_query.message
        await message.reply_text("🚫 You are not authorized to use this bot.")
        return
    message = getattr(update, "message", None)
    if message is None and hasattr(update, "callback_query") and update.callback_query:
        message = update.callback_query.message
    input_count = c.execute("SELECT COUNT(*) FROM input_channels").fetchone()[0]
    output_count = c.execute("SELECT COUNT(*) FROM output_channels").fetchone()[0]
    stats = f"📊 Stats:\nInput Channels: <b>{input_count}</b>\nOutput Channels: <b>{output_count}</b>"
    welcome_text = (
        "👋 <b>Welcome to ComboSender Bot!</b>\n"
        "<b>───────────────</b>\n"
        f"{stats}\n"
        "<b>───────────────</b>\n"
        "Manage your input/output channels and send combos easily using the buttons below:"
    )
    keyboard = [
        [InlineKeyboardButton("📋 Channels", callback_data="channels")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")


async def channels_callback(update: Update, context: CallbackContext):
    if not is_admin(update):
        query = getattr(update, "callback_query", None)
        if query:
            await query.answer()
            await query.edit_message_text("🚫 You are not authorized to use this bot.")
        else:
            await update.message.reply_text(
                "🚫 You are not authorized to use this bot."
            )
        return
    query = getattr(update, "callback_query", None)
    input_channels = [
        row[0] for row in c.execute("SELECT channel_id FROM input_channels")
    ]
    output_channels = [
        (row[0], row[1])
        for row in c.execute("SELECT channel_id, file_name FROM output_channels")
    ]
    text = "📥 Input Channels:\n" + (
        "\n".join(input_channels) if input_channels else "None"
    )
    text += "\n\n📤 Output Channels:\n" + (
        "\n".join([f"{cid} ({fname})" for cid, fname in output_channels])
        if output_channels
        else "None"
    )
    input_buttons = [
        [InlineKeyboardButton(f"❌ Delete {cid}", callback_data=f"del_input:{cid}")]
        for cid in input_channels
    ]
    output_buttons = [
        [InlineKeyboardButton(f"❌ Delete {cid}", callback_data=f"del_output:{cid}")]
        for cid, _ in output_channels
    ]
    keyboard = [
        [InlineKeyboardButton("➕ Add Input Channel", callback_data="add_input")],
        *input_buttons,
        [InlineKeyboardButton("📤 Add Output Channel", callback_data="add_output")],
        *output_buttons,
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query:
        await query.answer()
        await query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def back_to_main_callback(update: Update, context: CallbackContext):
    if not is_admin(update):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("🚫 You are not authorized to use this bot.")
        return
    query = update.callback_query
    await query.answer()
    await start(update, context)


async def callback_query_handler(update: Update, context: CallbackContext):
    if not is_admin(update):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("🚫 You are not authorized to use this bot.")
        return ConversationHandler.END
    query = update.callback_query
    if query.data == "channels":
        await channels_callback(update, context)
    elif query.data == "add_input":
        return await add_input_channel(update, context)
    elif query.data == "add_output":
        return await add_output_channel(update, context)
    elif query.data == "back_to_main":
        await back_to_main_callback(update, context)
    elif query.data.startswith("del_input:"):
        cid = query.data.split(":", 1)[1]
        c.execute("DELETE FROM input_channels WHERE channel_id=?", (cid,))
        conn.commit()
        await query.answer("Input channel deleted.")
        await channels_callback(update, context)
        return ConversationHandler.END
    elif query.data.startswith("del_output:"):
        cid = query.data.split(":", 1)[1]
        c.execute("DELETE FROM output_channels WHERE channel_id=?", (cid,))
        conn.commit()
        await query.answer("Output channel deleted.")
        await channels_callback(update, context)
        return ConversationHandler.END
    elif query.data == "skip_rights":
        await query.answer()
        channel_id, file_name = context.user_data.get(
            "pending_output_channel", ("", "results.txt")
        )
        await query.edit_message_text(
            f"✅ Output channel added: {channel_id} with file name: {file_name}"
        )
        await channels_callback(update, context)
        return ConversationHandler.END


async def add_input_channel(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="channels")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = getattr(update, "message", None)
    if message is None and hasattr(update, "callback_query"):
        message = update.callback_query.message
    article = (
        "<b>Input Channel</b>\n"
        "<b>───────────────</b>\n"
        "Enter the numeric ID of the Telegram channel or group to receive combo files.\n"
        "<i>Example: -123456789</i>"
    )
    await message.reply_text(
        f"{article}\n\nSend the input channel ID:",
        reply_markup=reply_markup,
        parse_mode="HTML",
    )
    return ADD_INPUT


async def save_input_channel(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return ConversationHandler.END
    channel_id = update.message.text.strip()
    try:
        int(channel_id)
    except ValueError:
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="channels")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ Invalid channel ID format. Please send a numeric ID.",
            reply_markup=reply_markup,
        )
        return ConversationHandler.END
    c.execute(
        "INSERT OR IGNORE INTO input_channels (channel_id) VALUES (?)", (channel_id,)
    )
    conn.commit()
    global input_channels
    input_channels = set(
        row[0] for row in c.execute("SELECT channel_id FROM input_channels")
    )
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="channels")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"✅ Input channel added: {channel_id}")
    await channels_callback(update, context)
    return ConversationHandler.END


async def add_output_channel(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="channels")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = getattr(update, "message", None)
    if message is None and hasattr(update, "callback_query"):
        message = update.callback_query.message
    article = (
        "<b>Output Channel</b>\n"
        "<b>───────────────</b>\n"
        "Enter the channel ID and .txt file name separated by a comma.\n"
        "<i>Example: -123456789,results.txt</i>"
    )
    await message.reply_text(
        f"{article}\n\nSend the output channel ID and txt file name:",
        reply_markup=reply_markup,
        parse_mode="HTML",
    )
    return ADD_OUTPUT


async def save_output_channel(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return ConversationHandler.END
    try:
        parts = [p.strip() for p in update.message.text.strip().split(",")]
        channel_id = parts[0]
        file_name = parts[1] if len(parts) > 1 else "results.txt"
        context.user_data["pending_output_channel"] = (channel_id, file_name)
        c.execute(
            "INSERT OR IGNORE INTO output_channels (channel_id, file_name) VALUES (?, ?)",
            (channel_id, file_name),
        )
        conn.commit()
        global output_channels
        output_channels = [
            (row[0], row[1])
            for row in c.execute("SELECT channel_id, file_name FROM output_channels")
        ]
        keyboard = [[InlineKeyboardButton("⏭️ Skip", callback_data="skip_rights")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Send the rights emails (one per line, format: email:pass).\nOr press Skip if you don't want to add any.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⏭️ Skip", callback_data="skip_rights")]]
            ),
        )
        return "RIGHTS_EMAILS"
    except Exception:
        await update.message.reply_text(
            "❌  Invalid channel ID or file name format. Please use the format: <code>channel_id,file_name</code>",
        )
    return ConversationHandler.END


async def save_rights_emails(update: Update, context: CallbackContext):
    if not is_admin(update):
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return ConversationHandler.END
    rights_emails = re.split(r"[\s,]+", update.message.text.strip())
    rights_emails = [email for email in rights_emails if email]
    channel_id, file_name = context.user_data.get(
        "pending_output_channel", ("", "results.txt")
    )
    c.execute(
        "INSERT OR IGNORE INTO output_channels (channel_id, file_name) VALUES (?, ?)",
        (channel_id, file_name),
    )
    conn.commit()
    global output_channels
    output_channels = [
        (row[0], row[1])
        for row in c.execute("SELECT channel_id, file_name FROM output_channels")
    ]
    for email in rights_emails:
        c.execute(
            "INSERT OR IGNORE INTO channel_rights_emails (channel_id, email) VALUES (?, ?)",
            (channel_id, email),
        )
        c.execute(
            "INSERT OR IGNORE INTO emails (email, status) VALUES (?, ?)",
            (email, "rights"),
        )
    conn.commit()
    await update.message.reply_text(
        f"✅ Output channel added: {channel_id} with file name: {file_name}\nRights emails saved."
    )
    await channels_callback(update, context)
    return ConversationHandler.END


async def handle_document(update: Update, context: CallbackContext):
    global input_channels, output_channels
    message = (
        update.message if update.message else getattr(update, "channel_post", None)
    )
    chat_id = str(update.effective_chat.id)
    if chat_id not in input_channels:
        return
    documents = []
    if message and getattr(message, "document", None):
        documents.append(message.document)
    if message and hasattr(message, "media_group_id") and message.media_group_id:
        recent_msgs = context.chat_data.get("recent_msgs", [])
        for msg in recent_msgs:
            if getattr(msg, "document", None):
                documents.append(msg.document)
    if not documents:
        return
    for doc in documents:
        file = await doc.get_file()
        base_name = doc.file_name
        file_path = os.path.join(TEMP_DIR, base_name)
        counter = 1
        while os.path.exists(file_path):
            name, ext = os.path.splitext(base_name)
            file_path = os.path.join(TEMP_DIR, f"{name}_{counter}{ext}")
            counter += 1
        await file.download_to_drive(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            combos = [line.strip() for line in f if line.strip()]

        c.execute("SELECT email, status FROM emails")
        db_emails = {row[0]: row[1] for row in c.fetchall()}
        new_combos = []
        for line in combos:
            try:
                email, _ = line.split(":", 1)
                if email not in db_emails:
                    new_combos.append(line)
            except ValueError:
                continue

        valid_combos = []
        invalid_combos = []
        for line in new_combos:
            try:
                email, _ = line.split(":", 1)
                result = checker_combo(line)
                if result:
                    valid_combos.append(line)
                    c.execute(
                        "INSERT OR IGNORE INTO emails (email, status) VALUES (?, ?)",
                        (email, "valid"),
                    )
                else:
                    invalid_combos.append(line)
                    if ":" in line:
                        spam_email = line.split(":", 1)[0]
                    else:
                        spam_email = line
                    c.execute(
                        "INSERT OR IGNORE INTO emails (email, status) VALUES (?, ?)",
                        (spam_email, "invalid"),
                    )
            except Exception:
                c.execute(
                    "INSERT OR IGNORE INTO emails (email, status) VALUES (?, ?)",
                    (line, "invalid"),
                )
                invalid_combos.append(line)
        conn.commit()

        for out_id, file_name in output_channels:
            out_path = os.path.join(TEMP_DIR, file_name)
            combos_to_write = valid_combos.copy()
            c.execute(
                "SELECT email FROM channel_rights_emails WHERE channel_id=?", (out_id,)
            )
            rights_emails = [row[0] for row in c.fetchall()]
            if combos_to_write and rights_emails:
                import random

                n_rights = int(0.4 * len(combos_to_write))
                selected_rights = []
                while len(selected_rights) < n_rights:
                    selected_rights.append(random.choice(rights_emails))
                for email in selected_rights:
                    attempts = 0
                    while True:
                        pos = random.randint(0, len(combos_to_write))
                        if (pos > 0 and combos_to_write[pos - 1] == email) or (
                            pos < len(combos_to_write) and combos_to_write[pos] == email
                        ):
                            attempts += 1
                            if attempts > 50:
                                break
                            continue
                        combos_to_write.insert(pos, email)
                        break
            if len(combos_to_write) <= 100:
                continue
            with open(out_path, "w", encoding="utf-8") as f:
                for line in combos_to_write:
                    f.write(line + "\n")
            if len(combos_to_write) == 0:
                continue
            try:
                await telethon_client.send_file(
                    int(out_id),
                    out_path,
                    mime_type="text/plain",
                )
            except Exception as e:
                if message:
                    await message.reply_text(
                        f"Telethon error sending to output channel {out_id}: {e}"
                    )

    for filename in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception:
            pass


async def process_document_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        combos = [line.strip() for line in f if line.strip()]
    c.execute("SELECT email, status FROM emails")
    db_emails = {row[0]: row[1] for row in c.fetchall()}
    new_combos = []
    for line in combos:
        try:
            email, _ = line.split(":", 1)
            if email not in db_emails:
                new_combos.append(line)
        except ValueError:
            continue
    valid_combos = []
    invalid_combos = []
    for line in new_combos:
        try:
            email, _ = line.split(":", 1)
            result = checker_combo(line)
            if result:
                valid_combos.append(line)
                c.execute(
                    "INSERT OR IGNORE INTO emails (email, status) VALUES (?, ?)",
                    (email, "valid"),
                )
            else:
                invalid_combos.append(line)
                if ":" in line:
                    spam_email = line.split(":", 1)[0]
                else:
                    spam_email = line
                c.execute(
                    "INSERT OR IGNORE INTO emails (email, status) VALUES (?, ?)",
                    (spam_email, "invalid"),
                )
        except Exception:
            c.execute(
                "INSERT OR IGNORE INTO emails (email, status) VALUES (?, ?)",
                (line, "invalid"),
            )
            invalid_combos.append(line)
    conn.commit()
    for out_id, file_name in output_channels:
        out_path = os.path.join(TEMP_DIR, file_name)
        combos_to_write = valid_combos.copy()
        c.execute(
            "SELECT email FROM channel_rights_emails WHERE channel_id=?", (out_id,)
        )
        rights_emails = [row[0] for row in c.fetchall()]
        if combos_to_write and rights_emails:
            import random

            n_rights = int(0.4 * len(combos_to_write))
            selected_rights = []
            while len(selected_rights) < n_rights:
                selected_rights.append(random.choice(rights_emails))
            for email in selected_rights:
                attempts = 0
                while True:
                    pos = random.randint(0, len(combos_to_write))
                    if (pos > 0 and combos_to_write[pos - 1] == email) or (
                        pos < len(combos_to_write) and combos_to_write[pos] == email
                    ):
                        attempts += 1
                        if attempts > 50:
                            break
                        continue
                    combos_to_write.insert(pos, email)
                    break
        if len(combos_to_write) <= 100:
            continue
        with open(out_path, "w", encoding="utf-8") as f:
            for line in combos_to_write:
                f.write(line + "\n")
        if len(combos_to_write) == 0:
            continue
        try:
            await telethon_client.send_file(
                int(out_id),
                out_path,
                mime_type="text/plain",
            )
        except Exception as e:
            pass
    for filename in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception:
            pass


def setup_telethon_handlers():
    @telethon_client.on(events.NewMessage(chats=[int(cid) for cid in input_channels]))
    async def telethon_handle_document(event):
        if not event.file or not event.file.name.endswith(".txt"):
            return
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
        base_name = event.file.name
        file_path = os.path.join(TEMP_DIR, base_name)
        counter = 1
        while os.path.exists(file_path):
            name, ext = os.path.splitext(base_name)
            file_path = os.path.join(TEMP_DIR, f"{name}_{counter}{ext}")
            counter += 1
        await event.download_media(file_path)
        if not os.path.exists(file_path):
            return
        await process_document_file(file_path)
