from src.config import logger
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
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
from src.database import save_phone_number, get_phone_number


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
        
        phone_number = get_phone_number(str(chat_id))
        if phone_number:
            chat_id = phone_number

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


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contact sharing to save phone numbers"""
    try:
        message = update.message
        if not message or not message.contact:
            return
            
        contact = message.contact
        chat_id = str(message.chat_id)
        phone_number = contact.phone_number
        
        # Save the phone number to database
        if save_phone_number(chat_id, phone_number):
            await context.bot.send_message(
                chat_id=message.chat_id,
                text="Спасибо! Ваш номер телефона сохранен."
            )
            log_info(f"Phone number for chat {chat_id} saved: {phone_number}", 'info')
        else:
            await context.bot.send_message(
                chat_id=message.chat_id,
                text="К сожалению, не удалось сохранить номер телефона. Пожалуйста, попробуйте позже."
            )
            log_info(f"Failed to save phone number for chat {chat_id}", 'error')
    except Exception as e:
        log_info(f"Error in handling contact message from {chat_id}", 'error')
        raise e


async def phone_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /phone command to request user's phone number"""
    try:
        chat_id = update.effective_chat.id
        
        # Check if we already have the phone number
        existing_phone = get_phone_number(str(chat_id))
        if existing_phone:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"У нас уже есть ваш номер телефона: {existing_phone}"
            )
            return
            
        # Create a keyboard with a button to share contact
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(text="Поделиться номером телефона", request_contact=True)]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="Пожалуйста, поделитесь вашим номером телефона, нажав на кнопку ниже.",
            reply_markup=keyboard
        )
        
        log_info(f"Phone number requested from chat {chat_id}", 'info')
    except Exception as e:
        log_info(f"Error in handling phone command from {chat_id}", 'error')
        raise e


async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command to show available commands"""
    try:
        chat_id = update.effective_chat.id
        
        menu_text = (
            "Добро пожаловать! Вот доступные команды:\n\n"
            "/phone - Поделиться номером телефона или узнать сохраненный номер\n"
            "/start - Показать это меню"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=menu_text
        )
        
        log_info(f"Menu displayed for chat {chat_id}", 'info')
    except Exception as e:
        log_info(f"Error in handling start command from {chat_id}", 'error')
        raise e