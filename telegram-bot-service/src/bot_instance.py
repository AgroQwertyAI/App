"""
Module for storing and accessing the global bot instance.
This prevents circular imports.
"""

# Global variable to store the Telegram bot instance
telegram_bot = None

def get_bot():
    """
    Returns the global bot instance.
    """
    return telegram_bot

def set_bot(bot):
    """
    Sets the global bot instance.
    """
    global telegram_bot
    telegram_bot = bot 