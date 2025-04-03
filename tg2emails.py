# --- Importing Necessary Libraries And Files ---
import logging
import requests
import os
import json # Added for JSON persistence
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, Defaults
from telegram import constants # Import constants for ParseMode

# --- Basic Configuration & Setup ---
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration Keys ---
MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN')
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
# Optional Defaults from .env
DEFAULT_SENDER_EMAIL = os.getenv('SENDER_EMAIL')
DEFAULT_RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')

# --- Validate Essential Configuration ---
if not MAILGUN_API_KEY or not MAILGUN_DOMAIN or not TELEGRAM_API_KEY:
    logger.critical("Essential environment variables (MAILGUN_API_KEY, MAILGUN_DOMAIN, TELEGRAM_API_KEY) not set. Exiting.")
    exit("Error: Missing essential configuration.")

# --- Persistence ---
USER_DATA_FILE = 'user_data.json'
USER_DATA = {} # In-memory cache

def load_user_data():
    """Loads user data from the JSON file."""
    global USER_DATA
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                USER_DATA = json.load(f)
                # Ensure keys are strings if loaded from JSON
                USER_DATA = {str(k): v for k, v in USER_DATA.items()}
                logger.info(f"Loaded user data from {USER_DATA_FILE}")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading user data from {USER_DATA_FILE}: {e}. Starting fresh.")
            USER_DATA = {}
    else:
        logger.info(f"{USER_DATA_FILE} not found. Starting with empty user data.")
        USER_DATA = {}

def save_user_data():
    """Saves user data to the JSON file."""
    global USER_DATA
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(USER_DATA, f, indent=4)
            logger.debug(f"Saved user data to {USER_DATA_FILE}") # Debug level for frequent saves
    except IOError as e:
        logger.error(f"Error saving user data to {USER_DATA_FILE}: {e}")

def get_user_setting(user_id: int, key: str, default=None):
    """Gets a specific setting for a user, falling back to default."""
    user_id_str = str(user_id)
    return USER_DATA.get(user_id_str, {}).get(key, default)

def set_user_setting(user_id: int, key: str, value):
    """Sets a specific setting for a user and saves."""
    user_id_str = str(user_id)
    if user_id_str not in USER_DATA:
        USER_DATA[user_id_str] = {}
    USER_DATA[user_id_str][key] = value
    save_user_data() # Save after every change

# --- Mailgun Email Function ---
def send_email(sender_email: str, recipient_email: str, file_path: str, file_name_orig: str) -> str:
    """Sends an email with a file attachment using Mailgun."""
    if not sender_email or not recipient_email:
        return "Error: Sender or Recipient email is not configured."

    logger.info(f"Attempting to send '{file_name_orig}' from {sender_email} to {recipient_email}")
    url = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"
    payload = {
        'from': sender_email,
        'to': recipient_email,
        'subject': f'File from Bot: {file_name_orig}', # Use original filename in subject
        'text': f'Document attached: {file_name_orig}', # Use original filename in body
    }

    response_text = f"Error: Could not send email. Unknown issue."
    status_code = 0

    try:
        with open(file_path, 'rb') as file:
            # Use original filename for the attachment metadata
            files = {'attachment': (file_name_orig, file, 'application/octet-stream')}
            response = requests.post(
                url,
                auth=('api', MAILGUN_API_KEY),
                data=payload,
                files=files
            )
            status_code = response.status_code
            response_text = response.text
    except FileNotFoundError:
         logger.error(f"File not found for sending: {file_path}")
         return f"Error: Could not find file {file_name_orig} to send."
    except Exception as e:
        logger.error(f"Error during Mailgun request: {e}", exc_info=True)
        return f"Error sending email: {e}"
    finally:
        # --- File Cleanup ---
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Removed temporary file: {file_path}")
            except OSError as e:
                logger.error(f"Error removing file {file_path}: {e}")

    if status_code == 200:
        logger.info(f"Email with '{file_name_orig}' sent successfully to {recipient_email}")
        # Escape recipient email for Markdown display
        escaped_recipient = recipient_email.replace('.', '\\.').replace('-', '\\-')
        return f"File sent successfully to `{escaped_recipient}`\\!" # Use Markdown for success msg
    else:
        logger.error(f"Mailgun error sending to {recipient_email}: {status_code} - {response_text}")
        # Escape potential markdown in error text
        error_summary = response_text[:150].replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        return f"Error sending file: {status_code} \- `{error_summary}`" # Use Markdown for error msg

# --- Telegram Bot Handlers ---

async def help_command(update: Update, context: CallbackContext) -> None:
    """Sends explanation on how to use the bot."""
    help_text = (
        "*Welcome\\!* Here's how to use me:\n\n"
        "*Setup:*\n"
        "1\\. `/setsender <your\\_authorized\\_email@example\\.com>`\n"
        "   Set the email address Mailgun will send *from*\\. This *must* be an address authorized in your Mailgun domain\\.\n\n"
        "*Managing Receivers:*\n"
        "2\\. `/newreceiver <label> <recipient\\_email@example\\.com>`\n"
        "   Save a recipient email with a short name \\(label\\), e\\.g\\., `/newreceiver kindle your\\_kindle@kindle\\.com`\\.\n"
        "3\\. `/viewreceivers`\n"
        "   Show all the recipient labels and emails you have saved\\.\n"
        "4\\. `/removereceiver <label>`\n"
        "   Delete a previously saved receiver label and its email\\.\n\n"
        "*Sending Files:*\n"
        "5\\. *Send me a document file* \\(PDF, MOBI, EPUB, etc\\.\\)\\.\n"
        "6\\. `/sendto <label>`\n"
        "   Send the *last document you uploaded* to the recipient saved with that label, e\\.g\\., `/sendto kindle`\\.\n\n"
        "_You need to set a sender email and at least one receiver before you can send files\\._"
    )
    # Help text is pre-escaped for MarkdownV2
    await update.message.reply_text(help_text, parse_mode=constants.ParseMode.MARKDOWN_V2)
    logger.info(f"User {update.effective_user.id} requested /help")

async def set_sender_command(update: Update, context: CallbackContext) -> None:
    """Sets the sender email address for the user."""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Please provide an email address\\. Usage: `/setsender <email@example\\.com>`", parse_mode=constants.ParseMode.MARKDOWN_V2)
        return

    sender_email = context.args[0]
    # Basic validation
    if '@' not in sender_email or '.' not in sender_email.split('@')[-1]:
         # Escape email for Markdown reply
        safe_email_display = sender_email.replace('.', '\\.').replace('-', '\\-')
        await update.message.reply_text(f"'{safe_email_display}' doesn't look like a valid email address\\.", parse_mode=constants.ParseMode.MARKDOWN_V2)
        return

    set_user_setting(user_id, 'sender_email', sender_email)
    logger.info(f"User {user_id} set sender email to {sender_email}")
     # Escape email for Markdown reply
    safe_email_display = sender_email.replace('.', '\\.').replace('-', '\\-')
    await update.message.reply_text(f"Sender email set to: `{safe_email_display}`", parse_mode=constants.ParseMode.MARKDOWN_V2)

async def new_receiver_command(update: Update, context: CallbackContext) -> None:
    """Adds or updates a recipient email with a label for the user."""
    user_id = update.effective_user.id
    if len(context.args) != 2:
        await update.message.reply_text("Usage: `/newreceiver <label> <email@example\\.com>` \\(e\\.g\\., `/newreceiver kindle your\\_kindle@kindle\\.com`\\)", parse_mode=constants.ParseMode.MARKDOWN_V2)
        return

    label, recipient_email = context.args[0].lower(), context.args[1] # Use lowercase label for consistency

    # Basic validation
    if not label.isalnum():
         await update.message.reply_text("Label should be alphanumeric \\(letters and numbers only\\)\\.", parse_mode=constants.ParseMode.MARKDOWN_V2)
         return
    if '@' not in recipient_email or '.' not in recipient_email.split('@')[-1]:
        # Escape email for Markdown reply
        safe_email_display = recipient_email.replace('.', '\\.').replace('-', '\\-')
        await update.message.reply_text(f"'{safe_email_display}' doesn't look like a valid email address\\.", parse_mode=constants.ParseMode.MARKDOWN_V2)
        return

    # Load existing receivers or create new dict
    receivers = get_user_setting(user_id, 'receivers', {})
    receivers[label] = recipient_email
    set_user_setting(user_id, 'receivers', receivers)

    logger.info(f"User {user_id} set receiver '{label}' to {recipient_email}")
    # Escape email for Markdown reply
    safe_email_display = recipient_email.replace('.', '\\.').replace('-', '\\-')
    await update.message.reply_text(f"Recipient `{label}` saved as: `{safe_email_display}`", parse_mode=constants.ParseMode.MARKDOWN_V2)

async def view_receivers_command(update: Update, context: CallbackContext) -> None:
    """Displays the user's saved receivers."""
    user_id = update.effective_user.id
    receivers = get_user_setting(user_id, 'receivers', {})

    if not receivers:
        await update.message.reply_text("You haven't saved any receivers yet\\. Use `/newreceiver <label> <email>` to add one\\.", parse_mode=constants.ParseMode.MARKDOWN_V2)
        logger.info(f"User {user_id} requested /viewreceivers, but has none saved.")
        return

    response_parts = ["*Your saved receivers:*"]
    for label, email in sorted(receivers.items()):
        # Manually escape problematic characters for MarkdownV2 within the email
        escaped_email = email.replace('.', '\\.').replace('-', '\\-')
        # Escape the leading hyphen for the list item
        response_parts.append(f"\\- `{label}`: {escaped_email}")
    response_message = "\n".join(response_parts)

    try:
        # Send using MarkdownV2
        await update.message.reply_text(response_message, parse_mode=constants.ParseMode.MARKDOWN_V2)
        logger.info(f"User {user_id} viewed their saved receivers with MarkdownV2.")
    except telegram.error.BadRequest as e:
        logger.error(f"Failed sending /viewreceivers with MarkdownV2: {e}. Message content:\n{response_message}")
        # Fallback: Try sending as plain text if Markdown fails
        plain_text_parts = ["Your saved receivers (plain text):"]
        for label, email in sorted(receivers.items()):
             plain_text_parts.append(f"- {label}: {email}") # Simple hyphen list
        plain_text_message = "\n".join(plain_text_parts)
        try:
            await update.message.reply_text(plain_text_message)
            logger.warning(f"Sent /viewreceivers as plain text fallback for user {user_id}.")
        except Exception as fallback_e:
            logger.error(f"Failed sending /viewreceivers even as plain text fallback: {fallback_e}")
            await update.message.reply_text("Sorry, there was an issue displaying your receivers list.")

async def remove_receiver_command(update: Update, context: CallbackContext) -> None:
    """Removes a saved receiver label and email for the user."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Please specify the label of the receiver to remove\\.\nUsage: `/removereceiver <label>`", parse_mode=constants.ParseMode.MARKDOWN_V2)
        return

    label_to_remove = context.args[0].lower() # Use lowercase for consistency

    receivers = get_user_setting(user_id, 'receivers', {})

    if label_to_remove in receivers:
        removed_email = receivers.pop(label_to_remove)
        set_user_setting(user_id, 'receivers', receivers)
        logger.info(f"User {user_id} removed receiver '{label_to_remove}' ({removed_email}).")
        # Escape email for Markdown reply
        safe_email_display = removed_email.replace('.', '\\.').replace('-', '\\-')
        await update.message.reply_text(f"✅ Receiver `{label_to_remove}` \\({safe_email_display}\\) has been removed\\.", parse_mode=constants.ParseMode.MARKDOWN_V2)
    else:
        logger.warning(f"User {user_id} tried to remove non-existent receiver label '{label_to_remove}'.")
        await update.message.reply_text(f"❌ Receiver label `{label_to_remove}` not found\\. Use `/viewreceivers` to see your current list\\.", parse_mode=constants.ParseMode.MARKDOWN_V2)
        available_labels = ", ".join(f"`{l}`" for l in sorted(receivers.keys()))
        if available_labels:
            await update.message.reply_text(f"*Available labels:* {available_labels}", parse_mode=constants.ParseMode.MARKDOWN_V2)

async def handle_document(update: Update, context: CallbackContext) -> None:
    """Stores the file ID and name of the received document in user_data."""
    if not update.message or not update.message.document:
        logger.warning("Received update without message or document.")
        return

    user_id = update.effective_user.id
    document = update.message.document

    # Store file_id and original filename in user_data (associated with the user)
    context.user_data['last_file_id'] = document.file_id
    context.user_data['last_file_name'] = document.file_name # Store original filename

    safe_file_name_display = document.file_name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
    logger.info(f"User {user_id} uploaded document '{document.file_name}' (ID: {document.file_id}). Stored for sending.")
    await update.message.reply_text(
        f"Received `{safe_file_name_display}`\\.\nUse `/sendto <label>` to send it, or `/viewreceivers` to see your labels\\.",
        parse_mode=constants.ParseMode.MARKDOWN_V2
    )

async def send_to_command(update: Update, context: CallbackContext) -> None:
    """Downloads the last uploaded document and sends it to the specified receiver label."""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Please specify a label\\. Usage: `/sendto <label>`", parse_mode=constants.ParseMode.MARKDOWN_V2)
        return

    label = context.args[0].lower()

    # --- Check Prerequisites ---
    sender_email = get_user_setting(user_id, 'sender_email', DEFAULT_SENDER_EMAIL)
    if not sender_email:
        await update.message.reply_text("Sender email not set\\. Use `/setsender <email>` first\\.", parse_mode=constants.ParseMode.MARKDOWN_V2)
        return

    receivers = get_user_setting(user_id, 'receivers', {})
    recipient_email = receivers.get(label)

    # Allow using 'default' label if DEFAULT_RECIPIENT_EMAIL is set in .env
    if not recipient_email and label == 'default' and DEFAULT_RECIPIENT_EMAIL:
         recipient_email = DEFAULT_RECIPIENT_EMAIL
         logger.info(f"User {user_id} using default recipient from .env for label 'default'")
    elif not recipient_email:
        await update.message.reply_text(f"No recipient found for label `{label}`\\. Use `/newreceiver {label} <email>` to add it, or `/viewreceivers` to see your list\\.", parse_mode=constants.ParseMode.MARKDOWN_V2)
        available_labels = ", ".join(f"`{l}`" for l in sorted(receivers.keys()))
        if available_labels:
            await update.message.reply_text(f"*Available labels:* {available_labels}", parse_mode=constants.ParseMode.MARKDOWN_V2)
        return

    if 'last_file_id' not in context.user_data or 'last_file_name' not in context.user_data:
        await update.message.reply_text("You haven't sent me a document recently\\. Please send a file first\\.", parse_mode=constants.ParseMode.MARKDOWN_V2)
        return

    file_id = context.user_data['last_file_id']
    original_file_name = context.user_data['last_file_name']

    # --- Prepare for Download ---
    temp_dir = './temp_downloads'
    os.makedirs(temp_dir, exist_ok=True)
    # Create a safe local filename, potentially different from original if it contains weird chars
    safe_local_filename = "".join(c for c in original_file_name if c.isalnum() or c in ('.', '_', '-')).strip()
    if not safe_local_filename: safe_local_filename = 'downloaded_file' # Fallback
    # Add user_id prefix to local filename for uniqueness in shared temp folder
    local_file_path = os.path.join(temp_dir, f"{user_id}_{safe_local_filename}")

    # --- Download and Send ---
    try:
        # Escape names/emails for status message display
        safe_display_filename = original_file_name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        safe_display_recipient = recipient_email.replace('.', '\\.').replace('-', '\\-')
        await update.message.reply_text(f"Preparing to send `{safe_display_filename}` to `{label}` \\({safe_display_recipient}\\)\\.\\.\\.", parse_mode=constants.ParseMode.MARKDOWN_V2)

        logger.info(f"User {user_id} requested sending file_id {file_id} ('{original_file_name}') to label '{label}' ({recipient_email})")

        file_object = await context.bot.get_file(file_id)
        await file_object.download_to_drive(local_file_path)
        logger.info(f"Successfully downloaded file_id {file_id} to: {local_file_path}")

        # Call the email sending function (passes original filename for email subject/attachment name)
        result = send_email(sender_email, recipient_email, local_file_path, original_file_name) # send_email handles cleanup

        # Send result back (already formatted with Markdown by send_email)
        await update.message.reply_text(result, parse_mode=constants.ParseMode.MARKDOWN_V2)
        logger.info(f"Attempted sending for user {user_id} to {label}. Result: {result}")

        # Clear the stored file info after processing attempt
        if 'last_file_id' in context.user_data: del context.user_data['last_file_id']
        if 'last_file_name' in context.user_data: del context.user_data['last_file_name']

    except Exception as e:
        logger.error(f"Error processing /sendto for user {user_id} label '{label}': {e}", exc_info=True)
        # Escape error message for Markdown
        error_message_safe = str(e).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        await update.message.reply_text(f"Sorry, an error occurred: {error_message_safe}", parse_mode=constants.ParseMode.MARKDOWN_V2)
        # Ensure cleanup even if download fails or other error occurs before sending
        if os.path.exists(local_file_path):
            try:
                os.remove(local_file_path)
                logger.info(f"Cleaned up temporary file after error: {local_file_path}")
            except OSError as cleanup_e:
                logger.error(f"Error removing file {local_file_path} after error: {cleanup_e}")


# --- Main Bot Execution Function ---
def main() -> None:
    """Sets up and runs the Telegram bot."""
    logger.info("Loading user data...")
    load_user_data()

    logger.info("Starting Telegram bot...")
    # Set default parse mode for cleaner handler code
    defaults = Defaults(parse_mode=constants.ParseMode.MARKDOWN_V2)
    app = Application.builder().token(TELEGRAM_API_KEY).defaults(defaults).build()

    # --- Handler Registration ---
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("setsender", set_sender_command))
    app.add_handler(CommandHandler("newreceiver", new_receiver_command))
    app.add_handler(CommandHandler("viewreceivers", view_receivers_command))
    app.add_handler(CommandHandler("removereceiver", remove_receiver_command))
    app.add_handler(CommandHandler("sendto", send_to_command))
    # Handles any document sent to the bot
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # --- Start Polling ---
    logger.info("Bot is polling...")
    # removed allowed_updates=Update.ALL_TYPES as it's the default and we handle specific types
    app.run_polling()

# --- Script Entry Point ---
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Log critical errors that stop the bot entirely
        logger.critical(f"Critical error running bot: {e}", exc_info=True)