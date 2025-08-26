import os
import random
import re
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
    Application,
)
from telethon import events
from src.data.database import c, conn
from src.utils.checker import filter_combos
from src.session.telethon_session import telethon_client
from config import ADMIN_IDS

TEMP_DIR = "temp"


class STATE:
    ADD_INPUT = 0
    ADD_OUTPUT = 1
    ADD_RIGHTS = 2


class CALLBACK:
    CHANNELS = "channels"
    ADD_INPUT = "add_input"
    ADD_OUTPUT = "add_output"
    SKIP_RIGHTS = "skip_rights"
    BACK_TO_MAIN = "back_to_main"
    DELETE_INPUT_PREFIX = "del_input:"
    DELETE_OUTPUT_PREFIX = "del_output:"


def get_db_input_channels() -> set:
    return {row[0] for row in c.execute("SELECT channel_id FROM input_channels")}


def get_db_output_channels() -> list:
    return c.execute("SELECT channel_id, file_name FROM output_channels").fetchall()


def admin_only(func):

    @wraps(func)
    async def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            message = "🚫 You are not authorized to perform this action."
            if update.callback_query:
                await update.callback_query.answer(message, show_alert=True)
            elif update.message:
                await update.message.reply_text(message)
            return
        return await func(update, context, *args, **kwargs)

    return wrapped


@admin_only
async def start(update: Update, context: CallbackContext):
    input_count = c.execute("SELECT COUNT(*) FROM input_channels").fetchone()[0]
    output_count = c.execute("SELECT COUNT(*) FROM output_channels").fetchone()[0]

    stats = f"📊 <b>Stats:</b>\nInput Channels: {input_count}\nOutput Channels: {output_count}"
    text = (
        "👋 <b>Welcome to ComboSender Bot!</b>\n"
        f"<b>───────────────</b>\n{stats}\n<b>───────────────</b>\n"
        "Manage your channels using the button below:"
    )
    keyboard = [[InlineKeyboardButton("📋 Channels", callback_data=CALLBACK.CHANNELS)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="HTML"
        )


@admin_only
async def channels_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    input_channels = get_db_input_channels()
    output_channels = get_db_output_channels()

    in_text = "\n".join(input_channels) if input_channels else "None"
    out_text = (
        "\n".join([f"`{cid}` ({fname})" for cid, fname in output_channels])
        if output_channels
        else "None"
    )
    text = f"📥 **Input Channels:**\n{in_text}\n\n📤 **Output Channels:**\n{out_text}"

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Add Input Channel", callback_data=CALLBACK.ADD_INPUT
            )
        ],
        *[
            [
                InlineKeyboardButton(
                    f"❌ Delete Input {cid}",
                    callback_data=f"{CALLBACK.DELETE_INPUT_PREFIX}{cid}",
                )
            ]
            for cid in input_channels
        ],
        [
            InlineKeyboardButton(
                "📤 Add Output Channel", callback_data=CALLBACK.ADD_OUTPUT
            )
        ],
        *[
            [
                InlineKeyboardButton(
                    f"❌ Delete Output {cid}",
                    callback_data=f"{CALLBACK.DELETE_OUTPUT_PREFIX}{cid}",
                )
            ]
            for cid, _ in output_channels
        ],
        [InlineKeyboardButton("⬅️ Back to Main", callback_data=CALLBACK.BACK_TO_MAIN)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text, reply_markup=reply_markup, parse_mode="Markdown"
    )


@admin_only
async def delete_channel(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    if data.startswith(CALLBACK.DELETE_INPUT_PREFIX):
        channel_id = data.replace(CALLBACK.DELETE_INPUT_PREFIX, "")
        c.execute("DELETE FROM input_channels WHERE channel_id=?", (channel_id,))
        await query.answer("✅ Input channel deleted.", show_alert=True)
    elif data.startswith(CALLBACK.DELETE_OUTPUT_PREFIX):
        channel_id = data.replace(CALLBACK.DELETE_OUTPUT_PREFIX, "")
        c.execute("DELETE FROM output_channels WHERE channel_id=?", (channel_id,))
        await query.answer("✅ Output channel deleted.", show_alert=True)

    conn.commit()
    await channels_menu(update, context)


@admin_only
async def ask_input_channel(update: Update, context: CallbackContext):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "Please send the numeric ID of the input channel."
    )
    return STATE.ADD_INPUT


@admin_only
async def save_input_channel(update: Update, context: CallbackContext):
    channel_id = update.message.text.strip()
    if not channel_id.lstrip("-").isdigit():
        await update.message.reply_text("❌ Invalid ID. Please send a numeric ID.")
        return ConversationHandler.END

    c.execute(
        "INSERT OR IGNORE INTO input_channels (channel_id) VALUES (?)", (channel_id,)
    )
    conn.commit()
    await update.message.reply_text(
        f"✅ Input channel `{channel_id}` added successfully."
    )
    return ConversationHandler.END


@admin_only
async def ask_output_channel(update: Update, context: CallbackContext):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "Send the output channel ID and the desired .txt file name, separated by a comma.\n\n"
        "Example: `-123456789,Hotmail_Results.txt`"
    )
    return STATE.ADD_OUTPUT


@admin_only
async def save_output_channel(update: Update, context: CallbackContext):
    try:
        parts = [p.strip() for p in update.message.text.split(",")]
        channel_id = parts[0]
        file_name = parts[1] if len(parts) > 1 else "results.txt"

        if not channel_id.lstrip("-").isdigit() or not file_name.endswith(".txt"):
            raise ValueError("Invalid format")

        context.user_data["pending_output"] = (channel_id, file_name)

        keyboard = [
            [InlineKeyboardButton("⏭️ Skip", callback_data=CALLBACK.SKIP_RIGHTS)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "✅ Output channel details received. Now, send the 'rights' emails (one per line or separated by spaces), or press Skip.",
            reply_markup=reply_markup,
        )
        return STATE.ADD_RIGHTS

    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Invalid format. Please use: `channel_id,file_name.txt`"
        )
        return ConversationHandler.END


@admin_only
async def save_rights_emails(update: Update, context: CallbackContext, skipped=False):
    channel_id, file_name = context.user_data.get("pending_output")

    c.execute(
        "INSERT OR IGNORE INTO output_channels (channel_id, file_name) VALUES (?, ?)",
        (channel_id, file_name),
    )

    message_text = (
        f"✅ Output channel `{channel_id}` with file `{file_name}` added successfully."
    )

    if not skipped:
        rights_emails = re.split(r"[\s,]+", update.message.text.strip())
        rights_emails = [email for email in rights_emails if ":" in email]

        if rights_emails:
            c.executemany(
                "INSERT OR IGNORE INTO channel_rights_emails (channel_id, email) VALUES (?, ?)",
                [(channel_id, email) for email in rights_emails],
            )
            c.executemany(
                "INSERT OR IGNORE INTO emails (email, status) VALUES (?, ?)",
                [(email.split(":", 1)[0], "rights") for email in rights_emails],
            )
            message_text += f"\nSaved {len(rights_emails)} rights emails."

    conn.commit()

    if update.callback_query:
        await update.callback_query.edit_message_text(
            message_text, parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(message_text, parse_mode="Markdown")

    context.user_data.pop("pending_output", None)
    return ConversationHandler.END


@admin_only
async def skip_rights_handler(update: Update, context: CallbackContext):
    await update.callback_query.answer()
    return await save_rights_emails(update, context, skipped=True)


async def process_document_file(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = {line.strip() for line in f if ":" in line.strip()}

        db_emails = {row[0] for row in c.execute("SELECT email FROM emails")}
        new_combos = {
            line for line in all_lines if line.split(":", 1)[0] not in db_emails
        }

        if not new_combos:
            print("[PROCESS] No new combos to process.")
            return

        valid_combos = filter_combos("\n".join(new_combos))
        valid_set = set(valid_combos)
        invalid_combos = new_combos - valid_set

        db_updates = []
        db_updates.extend([(combo.split(":", 1)[0], "valid") for combo in valid_combos])
        db_updates.extend(
            [(combo.split(":", 1)[0], "invalid") for combo in invalid_combos]
        )

        if db_updates:
            c.executemany(
                "INSERT OR IGNORE INTO emails (email, status) VALUES (?, ?)", db_updates
            )
            conn.commit()
            print(f"[DB] Updated status for {len(db_updates)} emails.")

        output_channels = get_db_output_channels()
        for out_id, out_fname in output_channels:
            if len(valid_combos) <= 100:
                print(
                    f"[SEND] Skipping channel {out_id}: Not enough valid combos ({len(valid_combos)})."
                )
                continue

            combos_to_write = valid_combos.copy()
            rights_emails = [
                row[0]
                for row in c.execute(
                    "SELECT email FROM channel_rights_emails WHERE channel_id=?",
                    (out_id,),
                )
            ]

            if combos_to_write and rights_emails:
                num_rights = int(0.4 * len(combos_to_write))
                selected_rights = random.choices(rights_emails, k=num_rights)
                for email in selected_rights:
                    combos_to_write.insert(
                        random.randint(0, len(combos_to_write)), email
                    )

            output_path = os.path.join(TEMP_DIR, out_fname)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(combos_to_write))

            try:
                await telethon_client.send_file(int(out_id), output_path)
                print(f"[SEND] File sent to channel {out_id}.")
            except Exception as e:
                print(f"[ERROR] Failed to send file to {out_id}: {e}")
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)

    except Exception as e:
        print(f"[ERROR] An error occurred in process_document_file: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[CLEANUP] Deleted temp file: {file_path}")


@telethon_client.on(events.NewMessage)
async def telethon_handler(event):
    input_channels = get_db_input_channels()
    if str(event.chat_id) not in input_channels:
        return

    if (
        not event.file
        or not event.file.name
        or not event.file.name.lower().endswith(".txt")
    ):
        return

    print(
        f"[TELETHON] Detected .txt file '{event.file.name}' in channel {event.chat_id}."
    )

    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    file_path = os.path.join(
        TEMP_DIR, f"{random.randint(1000, 9999)}_{event.file.name}"
    )

    try:
        await event.download_media(file_path)
        print(f"[DOWNLOAD] File downloaded to {file_path}")
        await process_document_file(file_path)
    except Exception as e:
        print(f"[ERROR] Failed to download or process file: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
