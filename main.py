from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import Conflict
from config import TELEGRAM_API_KEY, logger
from persistence import load_user_data
from bot_handlers import (
    help_command, set_sender_command, new_receiver_command,
    view_receivers_command, remove_receiver_command,
    handle_document, send_to_command
)
import time

def main():
    """Set up and run the Telegram bot."""
    while True:
        try:
            logger.info("Starting bot...")
            load_user_data()
            
            app = Application.builder().token(TELEGRAM_API_KEY).build()
            
            # Add command handlers
            app.add_handler(CommandHandler("help", help_command))
            app.add_handler(CommandHandler("setsender", set_sender_command))
            app.add_handler(CommandHandler("newreceiver", new_receiver_command))
            app.add_handler(CommandHandler("viewreceivers", view_receivers_command))
            app.add_handler(CommandHandler("removereceiver", remove_receiver_command))
            app.add_handler(CommandHandler("sendto", send_to_command))
            
            # Add document handler
            app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
            
            logger.info("Bot is running...")
            app.run_polling()
        except Conflict as e:
            logger.warning(f"Conflict error: {e}. Retrying in 5 seconds...")
            time.sleep(5)  # Wait 5 seconds before retrying
            continue
        except Exception as error:
            logger.critical(f"Bot crashed: {error}")
            raise

if __name__ == "__main__":
    main()