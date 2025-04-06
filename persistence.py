import json
import os
from config import logger

# File where user data is stored
USER_DATA_FILE = 'user_data.json'
# In-memory cache of user data
USER_DATA = {}

def load_user_data():
    """Load user data from JSON file into memory."""
    global USER_DATA
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as file:
                USER_DATA = json.load(file)
                # Convert all keys to strings (JSON might load as ints)
                USER_DATA = {str(key): value for key, value in USER_DATA.items()}
                logger.info(f"Loaded user data from {USER_DATA_FILE}")
        except (json.JSONDecodeError, IOError) as error:
            logger.error(f"Failed to load {USER_DATA_FILE}: {error}")
            USER_DATA = {}
    else:
        logger.info(f"No {USER_DATA_FILE} found, starting fresh")
        USER_DATA = {}

def save_user_data():
    """Save current user data to JSON file."""
    try:
        with open(USER_DATA_FILE, 'w') as file:
            json.dump(USER_DATA, file, indent=4)
            logger.debug(f"Saved user data to {USER_DATA_FILE}")
    except IOError as error:
        logger.error(f"Failed to save {USER_DATA_FILE}: {error}")

def get_user_setting(user_id: int, key: str, default=None):
    """Get a specific setting for a user, return default if not found."""
    user_id_str = str(user_id)
    return USER_DATA.get(user_id_str, {}).get(key, default)

def set_user_setting(user_id: int, key: str, value):
    """Set a specific setting for a user and save to file."""
    user_id_str = str(user_id)
    if user_id_str not in USER_DATA:
        USER_DATA[user_id_str] = {}
    USER_DATA[user_id_str][key] = value
    save_user_data()