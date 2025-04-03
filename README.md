# tg2kindle

Send a book to a Telegram bot and it will forward to Kindle

To set up a new Python virtual environment and install requests, follow these steps:

1. Navigate to Your Project Directory
2. Create a New Virtual Environment
   python3 -m venv env
3. Activate the Virtual Environment
   source env/bin/activate # For macOS/Linux
4. Upgrade pip and Install Dependencies
   python3 -m pip install --upgrade pip
   pip install requests python-dotenv requests python-telegram-bot
5. Verify Installation
   pip list | grep -E 'requests|python-dotenv|python-telegram-bot'
6. Run Your Script Again
   python3 tg2email.py
