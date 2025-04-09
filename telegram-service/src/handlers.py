import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.schemas import MessagePayload, ChatRegistrationSchema
import time
from src.auxiliary import (
    get_active_chats, 
    send_new_message, 
    register_chat, 
    unregister_chat,
    get_blob_photo,
    get_blob_video,
    get_blob_voice,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        
        # Initialize media variables
        images = []
        videos = []
        audio = None
        
        # Process photos if exist
        if message.photo:
            # Get the photo as base64
            image_blob = await get_blob_photo(message.photo)
            if image_blob:
                images.append(image_blob)
        
        # Process video if exists
        if message.video:
            # Get the video as base64
            video_blob = await get_blob_video(message.video)
            if video_blob:
                videos.append(video_blob)
        
        # Process voice messages if exist
        if message.voice:
            # Get the voice message as base64
            audio = await get_blob_voice(message.voice)
        
        # Process album/media group if available
        if message.media_group_id:
            # Store in context for album processing
            if not context.bot_data.get(message.media_group_id):
                context.bot_data[message.media_group_id] = {
                    'processed': False,
                    'expires': message.date.timestamp() + 60,  # Expire after 60 seconds
                    'chat_id': message.chat_id,
                    'images': [],
                    'videos': []
                }
            
            # If this message has a photo and we haven't seen it before, add it
            if message.photo and image_blob and image_blob not in context.bot_data[message.media_group_id]['images']:
                context.bot_data[message.media_group_id]['images'].append(image_blob)
                
            # If this message has a video and we haven't seen it before, add it
            if message.video and 'video_blob' in locals() and video_blob not in context.bot_data[message.media_group_id]['videos']:
                context.bot_data[message.media_group_id]['videos'].append(video_blob)
                
            # Use all media from the media group
            images = context.bot_data[message.media_group_id]['images']
            videos = context.bot_data[message.media_group_id]['videos']

        
        
        chat_id = message.chat_id
        sender = message.from_user
        sender_id = sender.id if sender else None
        sender_name = sender.username if sender and sender.username else\
            (sender.first_name if sender and sender.first_name else "")

        payload = MessagePayload(
            message_id=str(message.message_id),
            source_name="telegram", 
            chat_id=str(chat_id), 
            text=text, 
            sender_id=str(sender_id), 
            sender_name=sender_name, 
            images=images,
            videos=videos,
            audio=audio
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