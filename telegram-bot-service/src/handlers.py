from src.config import logger
from telegram import Update
from telegram.ext import ContextTypes
from src.schemas import MessagePayload, ChatRegistrationSchema
import time
from src.auxiliary import (
    send_new_message, 
    register_chat, 
    unregister_chat,
    get_blob_photo,
    get_blob_voice,
    log_info
)


async def cleanup_expired_media_groups(context: ContextTypes.DEFAULT_TYPE):
    """Clean up expired media groups from context.bot_data"""
    current_time = time.time()
    keys_to_remove = []
    
    for key, value in context.bot_data.items():
        if isinstance(value, dict) and 'expires' in value:
            if current_time > value['expires']:
                keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del context.bot_data[key]
        logger.info(f"Removed expired media group {key}")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            return
        
        # Extract text if available
        text = message.text if message.text else ""
        
        # Initialize media variables
        images = []
        audio = None
        
        # Process voice messages if exist
        if message.voice:
            # Get the voice message as base64
            audio = await get_blob_voice(message.voice)

        # Process photos if exist
        if message.photo:
            # Get the photo as base64
            image_blob = await get_blob_photo(message.photo)
            if image_blob:
                images.append(image_blob)
        
        # Process album/media group if available
        if message.media_group_id:
            # Store in context for album processing
            if not context.bot_data.get(message.media_group_id):
                context.bot_data[message.media_group_id] = {
                    'processed': False,
                    'expires': message.date.timestamp() + 60,  # Expire after 60 seconds
                    'chat_id': message.chat_id,
                    'images': [],
                }
            
            # If this message has a photo and we haven't seen it before, add it
            if message.photo and image_blob and image_blob not in context.bot_data[message.media_group_id]['images']:
                context.bot_data[message.media_group_id]['images'].append(image_blob)
                
            # Use all media from the media group
            images = context.bot_data[message.media_group_id]['images']
        
        chat_id = message.chat_id
        sender = message.from_user
        sender_id = sender.id if sender else None
        sender_name = sender.username if sender and sender.username else\
            (sender.first_name if sender and sender.first_name else "")

        payload = MessagePayload(
            message_id=str(message.message_id),
            chat_id=str(chat_id), 
            text=text, 
            sender_id=str(sender_id), 
            sender_name=sender_name, 
            images=images,
            audio=audio,
            is_private=message.chat.type == 'private'
        )

        await send_new_message(payload)
        log_info(f"Message {message.message_id} from {message.chat.id} processed", 'info')
    except Exception as e:
        log_info(f"Error in handling message {message.message_id} from {message.chat.id}", 'error')
        raise e


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
        
        # Send welcome message to the chat
        await context.bot.send_message(
            chat_id=chat_id,
            text="Привет! Я зафиксировал добавление в чат!"
        )

        log_info(f"Chat {chat_id} joined", 'info')
    except Exception as e:
        log_info(f"Error in handling chat {chat_id} join", 'error')
        raise e


async def chat_member_left_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_status = update.my_chat_member.new_chat_member.status
        if new_status not in ['left', 'kicked']:
            return

        chat = update.my_chat_member.chat
        chat_id = chat.id

        await unregister_chat(str(chat_id))
        log_info(f"Chat {chat_id} left", 'info')
    except Exception as e:
        log_info(f"Error in handling chat {chat_id} left", 'error')
        raise e