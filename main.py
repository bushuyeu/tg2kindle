from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import TELEGRAM_API_KEY, logger
from persistence import load_user_data
from tg_handlers import (  # Ensure this matches your file name
    help_command, set_sender_command, new_receiver_command,
    view_receivers_command, remove_receiver_command,
    handle_document, send_to_command
)

def main():
    """Set up and run the Telegram bot."""
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

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        logger.critical(f"Bot crashed: {error}")