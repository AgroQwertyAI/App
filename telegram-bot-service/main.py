from src.config import TELEGRAM_API_KEY
from src.bot_instance import set_bot

from src.handlers import (
    message_handler,
    chat_member_join_handler,
    chat_member_left_handler,
    cleanup_expired_media_groups,
    contact_handler,
    phone_command_handler,
    start_command_handler,
)
from src.schemas import MappingSchema
from telegram.ext import Application, MessageHandler, filters, ChatMemberHandler, CommandHandler
import asyncio
from fastapi import FastAPI
from src.message_router import message_router
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from src.auxiliary import log_info
from src.database import initialize_db, get_mapping as get_db_mapping

api = FastAPI(
    title="Telegram Bot Service", 
    description="A service for sending messages to Telegram"
)

api.include_router(message_router)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@api.get("/mapping", response_model=list[MappingSchema], tags=["mapping"])
async def get_mapping():
    mappings = get_db_mapping()
    return mappings

async def run_telegram_bot():
    token = TELEGRAM_API_KEY
    
    # Initialize database
    initialize_db()
    
    telegram_app = Application.builder().token(token).build()
    # Store the bot instance in the bot_instance module
    set_bot(telegram_app.bot)
    
    # Register handler for contacts to save phone numbers
    telegram_app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    # Register command handler for requesting phone number
    telegram_app.add_handler(CommandHandler("phone", phone_command_handler))
    # Register command handler for displaying menu
    telegram_app.add_handler(CommandHandler("start", start_command_handler))
    # Register the handler for text, photos, videos, and voice messages
    telegram_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VOICE, message_handler))
    # Register handler for bot added to group
    telegram_app.add_handler(ChatMemberHandler(chat_member_join_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    # Register handler for bot left the group
    telegram_app.add_handler(ChatMemberHandler(chat_member_left_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # Schedule cleanup job to run every minute
    job_queue = telegram_app.job_queue
    job_queue.run_repeating(cleanup_expired_media_groups, interval=60, first=10)
    
    # Start the bot
    await telegram_app.initialize()
    await telegram_app.start()
    log_info("Telegram bot started", 'info')
    # Start polling to receive updates from Telegram
    await telegram_app.updater.start_polling()
    
    try:
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        log_info("Telegram bot service ended", 'info')
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()


def start_uvicorn(loop):
    config = uvicorn.Config(api, loop=loop, host="0.0.0.0", port=7998)
    server = uvicorn.Server(config)
    loop.run_until_complete(server.serve())


def start_telegram_bot(loop):
    loop.create_task(run_telegram_bot())


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_telegram_bot(loop)
    start_uvicorn(loop)