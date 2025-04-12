import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Get the Telegram bot token from environment variable or use a default one for development
# Note: In production, this should always come from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7667447561:AAGBrVzUNsGOdgVohYyiqOSf1P6EM6H4M-8") 