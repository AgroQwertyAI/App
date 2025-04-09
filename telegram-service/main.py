import logging
from src.handlers import (
    message_handler,
    chat_member_join_handler,
    chat_member_left_handler,
    cleanup_expired_media_groups,
)
from telegram.ext import Application, MessageHandler, filters, ChatMemberHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    #token = os.environ["TELEGRAM_API_KEY"]
    token = "7667447561:AAGBrVzUNsGOdgVohYyiqOSf1P6EM6H4M-8"
    
    app = Application.builder().token(token).build()
    # Register the handler for text, photos, videos, and voice messages
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.VOICE, message_handler))
    # Register handler for bot added to group
    app.add_handler(ChatMemberHandler(chat_member_join_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    # Register handler for bot left the group
    app.add_handler(ChatMemberHandler(chat_member_left_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # Schedule cleanup job to run every minute
    job_queue = app.job_queue
    job_queue.run_repeating(cleanup_expired_media_groups, interval=60, first=10)

    app.run_polling()