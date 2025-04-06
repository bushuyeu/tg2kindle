import os
from dotenv import load_dotenv
import logging

# Set up logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment variables
MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN')
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
DEFAULT_SENDER_EMAIL = os.getenv('SENDER_EMAIL')
DEFAULT_RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')

# Check if essential configuration is present
if not all([MAILGUN_API_KEY, MAILGUN_DOMAIN, TELEGRAM_API_KEY]):
    logger.critical("Missing essential config: MAILGUN_API_KEY, MAILGUN_DOMAIN, or TELEGRAM_API_KEY")
    raise SystemExit("Error: Missing essential configuration.")
