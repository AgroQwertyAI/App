import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, ChatMemberHandler
from src.schemas import MessagePayload, ChatRegistrationSchema
from src.auxiliary import (
    get_active_chats, 
    send_new_message, 
    register_chat, 
    unregister_chat,
    get_blob_photo,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            return
    
        # Process only group messages
        if message.chat.type not in ['group', 'supergroup']:
            logger.info(f"Ignoring non-group message from chat id: {message.chat_id}")
            return

        active_chats = await get_active_chats()
        
        if str(message.chat_id) not in active_chats:
            logger.info(f"Chat id {message.chat_id} is not active. Skipping message.")
            return
        
        # Extract text if available
        text = message.text if message.text else ""
        
        # Process photo if exists
        image_blob = await get_blob_photo(message.photo)
        
        chat_id = message.chat_id
        sender = message.from_user
        sender_id = sender.id if sender else None
        sender_name = sender.username if sender and sender.username else\
            (sender.first_name if sender and sender.first_name else "")

        print(chat_id, text, sender_id, sender_name, image_blob)

        payload = MessagePayload(
            message_id=str(message.message_id),
            source_name="telegram", 
            chat_id=str(chat_id), 
            text=text, 
            sender_id=str(sender_id), 
            sender_name=sender_name, 
            image=image_blob
        )

        await send_new_message(payload)
    except Exception as e:
        logger.error(f"Error in message_handler: {e}")


async def chat_member_join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_status = update.my_chat_member.new_chat_member.status
        if new_status != 'member':
            return

        chat = update.my_chat_member.chat
        chat_id = chat.id
        chat_name = chat.title if getattr(chat, 'title', None) else 'Unknown Group'

        chat_registration = ChatRegistrationSchema(chat_id=str(chat_id), chat_name=chat_name)
        await register_chat(chat_registration)
    except Exception as e:
        logger.error(f"Error in chat_member_handler: {e}")


async def chat_member_left_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_status = update.my_chat_member.new_chat_member.status
        if new_status not in ['left', 'kicked']:
            return

        chat = update.my_chat_member.chat
        chat_id = chat.id

        await unregister_chat(str(chat_id))
    except Exception as e:
        logger.error(f"Error in chat_member_left_handler: {e}")


if __name__ == "__main__":
    #token = os.environ["TELEGRAM_API_KEY"]
    token = "7667447561:AAGBrVzUNsGOdgVohYyiqOSf1P6EM6H4M-8"
    
    app = Application.builder().token(token).build()
    # Register the handler for text and photo messages
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, message_handler))
    # Register handler for bot added to group
    app.add_handler(ChatMemberHandler(chat_member_join_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    # Register handler for bot left the group
    app.add_handler(ChatMemberHandler(chat_member_left_handler, ChatMemberHandler.MY_CHAT_MEMBER))

    app.run_polling()