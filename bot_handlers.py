from telegram import Update
from telegram.ext import ContextTypes
Ctx = ContextTypes.DEFAULT_TYPE
from config import logger, DEFAULT_SENDER_EMAIL, DEFAULT_RECIPIENT_EMAIL
from persistence import get_user_setting, set_user_setting
from email_service import send_email
import os

async def help_command(update: Update, context: Ctx):
    """Show how to use the bot."""
    help_text = (
        "Welcome! Here's how to use me:\n\n"
        "Setup:\n"
        "1. /setsender <your_email@example.com> - Set your sender email in bushuyeu.com domain. \n By default, all files are sent from p@bushuyeu.\n\n"
        "Receivers:\n"
        "2. /newreceiver <label> <email> - Add a recipient.\n"
        "3. /viewreceivers - List your recipients.\n"
        "4. /removereceiver <label> - Remove a recipient.\n\n"
        "Sending:\n"
        "5. Send me a document.\n"
        "6. /sendto <label> - Send last document to a recipient."
    )
    await update.message.reply_text(help_text)
    logger.info(f"User {update.effective_user.id} used /help")

async def set_sender_command(update: Update, context: Ctx):
    """Set the sender email for the user."""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setsender <email>")
        return

    email = context.args[0]
    if '@' not in email or '.' not in email.split('@')[-1]:
        await update.message.reply_text(f"{email} is not a valid email.")
        return

    set_user_setting(user_id, 'sender_email', email)
    await update.message.reply_text(f"Sender set to: {email}")
    logger.info(f"User {user_id} set sender to {email}")

async def new_receiver_command(update: Update, context: Ctx):
    """Add a new recipient with a label."""
    user_id = update.effective_user.id
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /newreceiver <label> <email>")
        return

    label, email = context.args[0].lower(), context.args[1]
    if not label.isalnum():
        await update.message.reply_text("Label must be alphanumeric.")
        return
    if '@' not in email or '.' not in email.split('@')[-1]:
        await update.message.reply_text(f"{email} is not a valid email.")
        return

    receivers = get_user_setting(user_id, 'receivers', {})
    receivers[label] = email
    set_user_setting(user_id, 'receivers', receivers)
    await update.message.reply_text(f"Added {label}: {email}")
    logger.info(f"User {user_id} added receiver {label}: {email}")

async def view_receivers_command(update: Update, context: Ctx):
    """Show all saved receivers."""
    user_id = update.effective_user.id
    receivers = get_user_setting(user_id, 'receivers', {})
    if not receivers:
        await update.message.reply_text("No receivers saved. Use /newreceiver.")
        return

    lines = ["Your receivers:"]
    for label, email in sorted(receivers.items()):
        lines.append(f"- {label}: {email}")
    await update.message.reply_text("\n".join(lines))
    logger.info(f"User {user_id} viewed receivers")

async def remove_receiver_command(update: Update, context: Ctx):
    """Remove a saved receiver."""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /removereceiver <label>")
        return

    label = context.args[0].lower()
    receivers = get_user_setting(user_id, 'receivers', {})
    if label in receivers:
        email = receivers.pop(label)
        set_user_setting(user_id, 'receivers', receivers)
        await update.message.reply_text(f"Removed {label}: {email}")
        logger.info(f"User {user_id} removed '{label}'")
    else:
        await update.message.reply_text(f"Label `{label}` not found. See `/viewreceivers`.")
        logger.warning(f"User {user_id} tried to remove unknown label '{label}'")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store a document sent by the user."""
    user_id = update.effective_user.id
    document = update.message.document
    
    # Add file size check (30 MB limit)
    max_size_mb = 30
    if document.file_size > max_size_mb * 1024 * 1024:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"File too large! Max size is {max_size_mb} MB."
        )
        logger.warning(f"User {user_id} uploaded file '{document.file_name}' that exceeds {max_size_mb} MB")
        return
    
    context.user_data['last_file_id'] = document.file_id
    context.user_data['last_file_name'] = document.file_name
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Got `{document.file_name}`. Use `/sendto <label>`."
    )
    logger.info(f"User {user_id} uploaded '{document.file_name}'")

async def send_to_command(update: Update, context: Ctx):
    """Send the last document to a receiver."""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /sendto <label>")
        return

    label = context.args[0].lower()
    sender_email = get_user_setting(user_id, 'sender_email', DEFAULT_SENDER_EMAIL)
    if not sender_email:
        await update.message.reply_text("Set sender with /setsender first.")
        return

    receivers = get_user_setting(user_id, 'receivers', {})
    recipient_email = receivers.get(label, DEFAULT_RECIPIENT_EMAIL if label == 'default' else None)
    if not recipient_email:
        await update.message.reply_text(f"No receiver for {label}. Use /newreceiver.")
        return

    if 'last_file_id' not in context.user_data:
        await update.message.reply_text("Send a document first.")
        return

    file_id = context.user_data['last_file_id']
    file_name = context.user_data['last_file_name']
    temp_path = f"temp_downloads/{user_id}_{file_name.replace('/', '_')}"
    os.makedirs("temp_downloads", exist_ok=True)

    try:
        await update.message.reply_text(f"Sending {file_name} to {recipient_email}...")
        file = await context.bot.get_file(file_id)
        await file.download_to_drive(temp_path)
        result = send_email(sender_email, recipient_email, temp_path, file_name)
        await update.message.reply_text(result)
        logger.info(f"User {user_id} sent '{file_name}' to '{label}'")
    except Exception as error:
        await update.message.reply_text(f"Error: {error}")
        logger.error(f"Send failed for user {user_id}: {error}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logger.info(f"Cleaned up {temp_path}")
        context.user_data.pop('last_file_id', None)
        context.user_data.pop('last_file_name', None)