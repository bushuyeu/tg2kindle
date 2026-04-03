import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from config import SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD, SENDER_EMAIL, KINDLE_EMAIL, logger


def send_email(file_path, file_name):
    """Send a file to Kindle via MXroute SMTP."""
    logger.info(f"Sending '{file_name}' from {SENDER_EMAIL} to {KINDLE_EMAIL}")

    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = KINDLE_EMAIL
        msg["Subject"] = file_name
        msg.attach(MIMEText(f"Document: {file_name}", "plain"))

        with open(file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={file_name}")
            msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Sent '{file_name}' to {KINDLE_EMAIL}")
        return "Sent to Kindle!"

    except Exception:
        logger.exception("Email sending failed")
        return "Error sending email. Check logs."
