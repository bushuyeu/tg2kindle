# --- Importing Necessary Libraries And Files ---

# Import the logging library for recording events, errors, and informational messages.
import logging
# Import the requests library to make HTTP requests (e.g.: to the Mailgun API).
import requests
# Import the os library for interacting with the operating system, primarily used here for accessing environment variables (os.getenv) and file system operations (os.path.basename, os.remove, os.path.exists).
import os  
# Import the load_dotenv function from the python-dotenv library. This function loads environment variables from a .env file into the system's environment. 
# Reference: https://github.com/theskumar/python-dotenv
from dotenv import load_dotenv
# Import the Update class from Telegram library. Represents an incoming update (e.g.: a message).
# Reference: https://docs.python-telegram-bot.org/en/v20.7/telegram.update.html
from telegram import Update
# Import necessary components from telegram.ext (the main module for building bots).
# Application: The core class that runs the bot.
# CommandHandler: Handles messages starting with '/' commands.
# MessageHandler: Handles regular messages based on filters.
# filters: Used to filter incoming messages (e.g., only handle documents).
# CallbackContext: A dictionary-like object to store and share bot/user data.
# Reference: https://docs.python-telegram-bot.org/en/v20.7/telegram.ext.application.html
# Reference: https://docs.python-telegram-bot.org/en/v20.7/telegram.ext.commandhandler.html
# Reference: https://docs.python-telegram-bot.org/en/v20.7/telegram.ext.messagehandler.html
# Reference: https://docs.python-telegram-bot.org/en/v20.7/telegram.ext.filters.html
# Reference: https://docs.python-telegram-bot.org/en/v20.7/telegram.ext.callbackcontext.html
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext


# Load environment variables from .env file
# '.env' should be added to .gitignore file to avoid committing sensitive date
load_dotenv() 

# Configure the root logger for the application.
logging.basicConfig(
    # Set the minimum severity level of messages to log (INFO includes INFO, WARNING, ERROR, CRITICAL).
    level=logging.INFO,  
    # Define the format for log messages: timestamp, log level name, and the message itself.
    # Reference: https://docs.python.org/3/library/logging.html#logrecord-attributes
    format='%(asctime)s - %(levelname)s - %(message)s' 
)

# Get a specific logger instance for this module (__name__ resolves to the module's name). 
logger = logging.getLogger(__name__)

# --- Configuration Section ---

# Create a dictionary to hold the application's configuration values.
CONFIG = {
    # Retrieve the Mailgun API key from environment variables. os.getenv returns None if the variable isn't set.
    # Reference: https://docs.python.org/3/library/os.html#os.getenv
    'mailgun_api_key': os.getenv('MAILGUN_API_KEY'),

    # Retrieve the Mailgun domain name from environment variables.
    'mailgun_domain': os.getenv('MAILGUN_DOMAIN'),

    # Retrieve the sender email address (must be authorized with Mailgun) from environment variables.
    'sender_email': os.getenv('SENDER_EMAIL'),

    # Retrieve the recipient email address (Kindle address) from environment variables.
    'recipient_email': os.getenv('RECIPIENT_EMAIL'),

    # Retrieve the Telegram Bot API key (token) from environment variables.
    'telegram_api_key': os.getenv('TELEGRAM_API_KEY'),
}

# --- Configuration Validation ---

# Iterate through the key-value pairs in the CONFIG dictionary.
for key, value in CONFIG.items():
    # Check if the value for a configuration key is None (meaning the environment variable was not found).
    if value is None:

        # Log a critical error message indicating which configuration variable is missing.
        logger.error(f"Configuration error: Environment variable '{key.upper()}' not set.")
        
        # Exit the script immediately with an error message. 
        # Alternatively, raise a ValueError to handle this more gracefully later.
        exit(f"Error: Missing configuration for {key.upper()}")

# --- Mailgun Email Function ---
# Define a function to send an email with a file attachment using the Mailgun API.
# Type hinting: Specifies that file_path should be a string and the function returns a string.

def send_email_to_kindle(file_path: str) -> str:
    # Construct the URL for the Mailgun messages API endpoint using an f-string and the configured (in the Mailgun) domain.
    # Reference: https://documentation.mailgun.com/en/latest/api-sending.html#sending
    url = f"https://api.mailgun.net/v3/{CONFIG['mailgun_domain']}/messages"
    
    # Define the email payload (non-file parts) as a dictionary.
    payload = {
        'from': CONFIG['sender_email'], # Sender email address from config.
        'to': CONFIG['recipient_email'], # Recipient email address (Kindle) from config.
        'subject': 'Sending file to Kindle', # Email, subject line
        'text': 'Here is your requested document.', #Email, body text
    }
    
    # Open the specified file in binary read mode ('rb'). 
    # The 'with' statement ensures the file is automatically closed even if errors occur.
    with open(file_path, 'rb') as file:
        # Extract only the filename from the potentially full path using os.path.basename.
        # This prevents sending the full local path as the attachment name.
        # Reference: https://docs.python.org/3/library/os.path.html#os.path.basename
        filename = os.path.basename(file_path) 

        # Prepare the file data for the POST request. 'requests' expects a dictionary where the key ('attachment') is the form field name, and the value is a tuple:
        # (filename_to_use, file_object, content_type). 'application/octet-stream' is a generic binary type.
        files = {'attachment': (filename, file, 'application/octet-stream')} 
        
        # Make a POST request to the Mailgun API URL.
        # Reference: https://requests.readthedocs.io/en/latest/user/quickstart/#post-a-multipart-encoded-file
        response = requests.post(
            url,
            # Use HTTP Basic Authentication with 'api' as the username and the Mailgun API key as the password.
            auth=('api', CONFIG['mailgun_api_key']),
            # Pass the non-file payload data (from, to, subject, text).
            data=payload,
            # Pass the file data prepared above. 'requests' will handle the multipart/form-data encoding.
            files=files
        )
    
    # --- File Cleanup ---

    # Attempt to remove the temporary file that was downloaded from Telegram.
    try:
        os.remove(file_path)
        # Log that the temporary file was successfully removed.
        logger.info(f"Removed temporary file: {file_path}")

    # Catch an OSError if the file couldn't be removed (e.g., permissions issue, file not found).
    except OSError as e:

        # Log an error indicating the failure to remove the file.
        logger.error(f"Error removing file {file_path}: {e}")

    # Check the HTTP status code of the response from Mailgun. 200 means success.
    # Return a user-friendly success message or an error message including the status code and response text.
    return "File sent successfully!" if response.status_code == 200 else f"Error: {response.status_code} - {response.text}"

# --- Telegram Bot Handlers ---

# Define an asynchronous function to handle the /start command.
# 'async def' is used because python-telegram-bot v20+ is built on asyncio.
# Reference: https://docs.python-telegram-bot.org/en/v20.7/index.html#getting-started
async def start(update: Update, context: CallbackContext) -> None:
    # Send a reply message back to the user who sent the /start command.
    # 'await' is used to call asynchronous functions (like sending messages).
    # Reference: https://docs.python-telegram-bot.org/en/v20.7/telegram.message.html#telegram.Message.reply_text
    await update.message.reply_text('Hello! Send me a file, and I’ll send it to your Kindle.')
    # Log that the /start command was received.
    logger.info("Received /start command")

# Define an asynchronous function to handle incoming messages containing documents to send to Kindle
async def handle_document(update: Update, context: CallbackContext) -> None:
    # Check if the update contains a message and that the message contains a document. 
    # This prevents errors if the handler is somehow triggered by non-document messages.
    if not update.message or not update.message.document:
        logger.warning("Received message without document.")
        return # Exit the handler if no document is present.

    # Get the Document object from the incoming message.
    # Reference: https://docs.python-telegram-bot.org/en/v20.7/telegram.document.html
    document = update.message.document
    # Define the local path where the file will be saved. Using './' means the current directory.
    # Note: If multiple users use the bot simultaneously, filenames could clash. 
    # Consider using a temporary directory (tempfile module) or adding user IDs/timestamps to filenames.
    file_path = f'./{document.file_name}' 
    
    # --- File Handling and Sending Logic ---
    # Use a try...except block to catch potential errors during file download or sending.
    try:
        # Log the attempt to download the file.
        logger.info(f"Attempting to download: {document.file_name}")
        # Get a File object, which represents the file on Telegram's servers and provides download methods.
        # Reference: https://docs.python-telegram-bot.org/en/v20.7/telegram.document.html#telegram.Document.get_file
        file_object = await document.get_file()
        # Download the file content to the specified local path.
        # Reference: https://docs.python-telegram-bot.org/en/v20.7/telegram.file.html#telegram.File.download_to_drive
        await file_object.download_to_drive(file_path)   
        # Log successful download.
        logger.info(f"Successfully downloaded to: {file_path}")
        
        # Call the function to send the downloaded file via email using Mailgun.
        # The send_email_to_kindle function now also handles deleting the file afterwards.
        result = send_email_to_kindle(file_path) # send_email_to_kindle now handles cleanup
        
        # Send the result message (success or error) back to the user in Telegram.
        await update.message.reply_text(result)
        
        # Log the outcome of processing the document.
        logger.info(f"Processed document: {document.file_name}. Result: {result}")
    
    # Catch any exception that might occur during the try block.
    except Exception as e:
        # Log the error, including the traceback (exc_info=True) for detailed debugging.
        logger.error(f"Error handling document {document.file_name}: {e}", exc_info=True)
        # Inform the user that an error occurred. Avoid sending detailed internal errors to the user.
        await update.message.reply_text(f"Sorry, an error occurred while processing your file: {e}")
        # --- Cleanup on Error ---
        # Check if the file was downloaded (exists) before the error occurred during sending.
        if os.path.exists(file_path):
            # Try to remove the partially processed file.
            try:
                 os.remove(file_path)
                 logger.info(f"Cleaned up partially processed file: {file_path}")

            # Catch potential errors during this cleanup attempt.
            except OSError as cleanup_e:
                 logger.error(f"Error removing file {file_path} after error: {cleanup_e}")

# --- Main Bot Execution Function ---
# Define the main function to set up and run the bot.
def main() -> None:
    # Log that the bot is starting.
    logger.info("Starting Telegram bot...")
    
    # --- Pre-run Check ---
    # Ensure the Telegram API key was loaded successfully before trying to build the application.
    if not CONFIG['telegram_api_key']:
        # Log a critical error if the key is missing and stop execution.
        logger.critical("TELEGRAM_API_KEY not found in environment variables. Exiting.")
        
        return # Exit the main function
    
     # --- Bot Setup ---
     # Create the Application instance using the builder pattern.
     # Provide the Telegram Bot Token from the configuration.
    app = Application.builder().token(CONFIG['telegram_api_key']).build()
     
    # --- Handler Registration ---
    # Register a CommandHandler. It will call the 'start' function when a '/start' command is received.
    app.add_handler(CommandHandler("start", start))

    # Register a MessageHandler. 
    # filters.Document.ALL ensures it triggers for any message containing any type of document.
    # It will call the 'handle_document' function for such messages.
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document)) 
    
    # --- Start Polling ---
    # Log that the bot is starting to poll for updates.
    logger.info("Bot is polling...")

    # Start the bot's polling mechanism. It continuously fetches updates from Telegram.
    # allowed_updates=Update.ALL_TYPES specifies that the bot should receive all types of updates.
    # Reference: https://docs.python-telegram-bot.org/en/v20.7/telegram.ext.application.html#telegram.ext.Application.run_polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# --- Script Entry Point ---
# This standard Python construct checks if the script is being run directly (not imported as a module).
if __name__ == '__main__':
    # Use a try...except block to catch any exceptions that might occur during bot startup or runtime that aren't caught elsewhere (like critical configuration issues).
    try:
        main() # Call the main function to start the bot.
    
    # Catch any generic Exception.
    except Exception as e:
        # Log a critical error, including the traceback, if the bot fails catastrophically.
        logger.error(f"Critical error running bot: {e}", exc_info=True) 