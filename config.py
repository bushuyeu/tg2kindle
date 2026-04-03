import os
import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
KINDLE_EMAIL = os.getenv("KINDLE_EMAIL")

SMTP_SERVER = os.getenv("SMTP_SERVER", "mail.mxlogin.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

_allowed = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = [int(uid.strip()) for uid in _allowed.split(",") if uid.strip()] if _allowed else []

if not all([TELEGRAM_API_KEY, KINDLE_EMAIL, SMTP_EMAIL, SMTP_PASSWORD]):
    logger.critical("Missing config — check .env")
    raise SystemExit("Error: Missing essential configuration.")
