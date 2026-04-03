import os
import re
from urllib.parse import urlparse, unquote

import requests
from telegram.ext import Application, MessageHandler, filters

from config import TELEGRAM_API_KEY, ALLOWED_USERS, logger
from email_service import send_email

MAX_SIZE_MB = 100
KINDLE_FORMATS = {".pdf", ".epub", ".txt", ".html", ".htm", ".rtf",
                  ".jpeg", ".jpg", ".gif", ".png", ".bmp"}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/pdf,*/*",
})


async def handle_document(update, context):
    """Receive a document (direct or forwarded) and send it to Kindle."""
    user_id = update.effective_user.id
    document = update.message.document
    file_name = document.file_name or "document"

    ext = os.path.splitext(file_name)[1].lower()
    if ext not in KINDLE_FORMATS:
        supported = ", ".join(sorted(KINDLE_FORMATS))
        await update.message.reply_text(f"Unsupported format: {ext}\nKindle accepts: {supported}")
        return

    if document.file_size > MAX_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(f"File too large! Max {MAX_SIZE_MB} MB.")
        return

    await update.message.reply_text(f"Sending {file_name} to Kindle...")
    temp_path = f"temp_downloads/{user_id}_{os.path.basename(file_name)}"
    os.makedirs("temp_downloads", exist_ok=True)

    try:
        file = await context.bot.get_file(document.file_id)
        await file.download_to_drive(temp_path)
        result = send_email(temp_path, file_name)
        await update.message.reply_text(result)
        logger.info(f"User {user_id} sent '{file_name}' to Kindle")
    except Exception as e:
        if "too big" in str(e).lower():
            await update.message.reply_text("File too large for Telegram (>20MB). Send a direct link instead.")
        else:
            logger.exception(f"Send failed for user {user_id}")
            await update.message.reply_text("Failed to send. Please try again.")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def extract_url(message):
    """Extract a URL from message text or caption."""
    text = message.text or message.caption or ""
    urls = re.findall(r'https?://\S+', text)
    if not urls:
        return None
    return resolve_url(urls[0])


def resolve_url(url):
    """Convert sharing URLs to direct download URLs."""
    # Google Drive: /file/d/FILE_ID/view -> direct download
    match = re.search(r'drive\.google\.com/file/d/([^/]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    # Dropbox: change dl=0 to dl=1
    if "dropbox.com" in url:
        return re.sub(r'dl=0', 'dl=1', url)

    return url


def url_to_filename(url):
    """Derive a filename from a URL, ensuring it has a Kindle-compatible extension."""
    parsed = urlparse(url)
    name = unquote(os.path.basename(parsed.path)) or "download"

    # Check if it already has a valid extension
    ext = os.path.splitext(name)[1].lower()
    if ext in KINDLE_FORMATS:
        return name

    # No valid extension — detect from content-type
    try:
        ct = SESSION.head(url, timeout=10, allow_redirects=True).headers.get("content-type", "")
        if "epub" in ct:
            name += ".epub"
        elif "pdf" in ct or "octet-stream" in ct:
            name += ".pdf"
        else:
            name += ".pdf"
    except Exception:
        name += ".pdf"
    return name


async def handle_url(update, context):
    """Download a file from a URL (direct or forwarded) and send it to Kindle."""
    user_id = update.effective_user.id
    url = extract_url(update.message)
    if not url:
        return

    file_name = url_to_filename(url)
    await update.message.reply_text(f"Downloading {file_name}...")
    temp_path = f"temp_downloads/{user_id}_{os.path.basename(file_name)}"
    os.makedirs("temp_downloads", exist_ok=True)

    try:
        response = SESSION.get(url, timeout=60, stream=True, allow_redirects=True)
        response.raise_for_status()

        size = int(response.headers.get("content-length", 0))
        if size > MAX_SIZE_MB * 1024 * 1024:
            await update.message.reply_text(f"File too large! Max {MAX_SIZE_MB} MB.")
            return

        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)

        await update.message.reply_text(f"Sending {file_name} to Kindle...")
        result = send_email(temp_path, file_name)
        await update.message.reply_text(result)
        logger.info(f"User {user_id} sent URL '{file_name}' to Kindle")
    except requests.RequestException as e:
        logger.exception(f"Download failed for user {user_id}")
        await update.message.reply_text(f"Download failed: {e}")
    except Exception:
        logger.exception(f"Send failed for user {user_id}")
        await update.message.reply_text("Failed to send. Please try again.")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def main():
    user_filter = filters.User(user_id=ALLOWED_USERS) if ALLOWED_USERS else filters.ALL
    url_pattern = filters.Regex(r'https?://')

    app = Application.builder().token(TELEGRAM_API_KEY).build()
    app.add_handler(MessageHandler(filters.Document.ALL & user_filter, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & url_pattern & user_filter, handle_url))
    app.add_handler(MessageHandler(filters.CaptionRegex(r'https?://') & user_filter, handle_url))
    logger.info("Bot started — send a file or URL, it goes to Kindle.")
    app.run_polling()


if __name__ == "__main__":
    main()
