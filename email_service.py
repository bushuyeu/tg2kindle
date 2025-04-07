import requests
import os
from config import MAILGUN_API_KEY, MAILGUN_DOMAIN, logger

def send_email(sender_email: str, recipient_email: str, file_path: str, file_name: str) -> str:
    """Send an email with a file attachment using Mailgun."""
    if not sender_email or not recipient_email:
        return "Error: Sender or recipient email missing."

    logger.info(f"Sending '{file_name}' from {sender_email} to {recipient_email}")
    url = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"
    payload = {
        'from': sender_email,
        'to': recipient_email,
        'subject': f'File from Telegram 2 Kindle',
        'text': f'Document attached: {file_name}',
    }

    try:
        with open(file_path, 'rb') as file:
            files = {'attachment': (file_name, file, 'application/octet-stream')}
            response = requests.post(url, auth=('api', MAILGUN_API_KEY), data=payload, files=files)
        
        if response.status_code == 200:
            logger.info(f"Email '{file_name}' sent to {recipient_email}")
            return f"File sent successfully to {recipient_email}!"
        else:
            error_msg = response.text[:150].replace('_', '\\_').replace('*', '\\*')
            logger.error(f"Mailgun error: {response.status_code} - {response.text}")
            return f"Error sending file: {response.status_code} - `{error_msg}`"

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return f"Error: Could not find file {file_name}."
    except Exception as error:
        logger.error(f"Email sending failed: {error}")
        return f"Error sending email: {error}"
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up {file_path}")
            except OSError as error:
                logger.error(f"Cleanup failed for {file_path}: {error}")