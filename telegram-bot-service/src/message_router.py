from fastapi import APIRouter, HTTPException, Body
import aiohttp
import base64
from src.schemas import SendMessageText, SendMessageImage, SendMessageFile
from src.bot_instance import get_bot
from src.auxiliary import log_info
from src.database import get_chat_id_by_phone_number
message_router = APIRouter(
    tags=["Telegram Bot Service"]
)

# Endpoint to send a text message
@message_router.post("/send_message", status_code=204, response_model=None)
async def send_message(message: SendMessageText = Body(...)):
    try:
        if not message.chat_id or not message.text:
            raise HTTPException(status_code=400, detail="Both chat_id and text parameters are required")
        
        # Get the bot instance
        bot = get_bot()
        if bot is None:
            raise HTTPException(status_code=503, detail="Telegram bot is not initialized yet")
        
        chat_id = get_chat_id_by_phone_number(message.chat_id)
        log_info(f"Chat ID: {chat_id}", 'info')
        if chat_id is None:
            chat_id = message.chat_id
            
        # Send the message using telegram bot
        await bot.send_message(chat_id=chat_id, text=message.text)
        log_info(f"Message sent to {chat_id}: {message.text}", 'info')

    except Exception as e:
        log_info(f"Error in sending message to {chat_id}", 'error')
        raise e

# Endpoint to send an image
@message_router.post("/send_image", status_code=204, response_model=None)
async def send_image(message: SendMessageImage = Body(...)):
    try:
        if not message.chat_id or not message.image:
            raise HTTPException(status_code=400, detail="Both chat_id and image parameters are required")
        
        # Get the bot instance
        bot = get_bot()
        if bot is None:
            raise HTTPException(status_code=503, detail="Telegram bot is not initialized yet")
        
        # Handle different image formats
        image_data = None
        
        if message.image.startswith(("http://", "https://")):
            # Image is a URL
            async with aiohttp.ClientSession() as session:
                async with session.get(message.image) as response:
                    if response.status != 200:
                        raise HTTPException(status_code=400, detail="Failed to download image from URL")
                    image_data = await response.read()
        
        elif message.image.startswith("data:"):
            try:
                # Handle data URI format
                image_base64 = message.image.split(",")[1]
                image_data = base64.b64decode(image_base64)
            except IndexError:
                raise HTTPException(status_code=400, detail="Invalid data URI format")
            except Exception:
                raise HTTPException(status_code=400, detail="Failed to decode base64 image")
        
        else:
            # Assume it's a base64 string
            try:
                image_data = base64.b64decode(message.image)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid base64 image")
            
        chat_id = get_chat_id_by_phone_number(message.chat_id)
        if chat_id is None:
            chat_id = message.chat_id
        
        await bot.send_photo(chat_id=chat_id, photo=image_data)
        log_info(f"Image sent to {chat_id}", 'info')
    except Exception as e:
        log_info(f"Error in sending image to {chat_id}", 'error')
        raise e

# Endpoint to send a file
@message_router.post("/send_file", status_code=204, response_model=None)
async def send_file(message: SendMessageFile = Body(...)):
    try:
        if not message.chat_id or not message.file:
            raise HTTPException(status_code=400, detail="Both chat_id and file parameters are required")
        
        # Get the bot instance
        bot = get_bot()
        if bot is None:
            raise HTTPException(status_code=503, detail="Telegram bot is not initialized yet")
        
        # Handle different file formats
        file_data = None
        filename = message.filename or "file"
        
        if message.file.startswith(("http://", "https://")):
            # File is a URL
            async with aiohttp.ClientSession() as session:
                async with session.get(message.file) as response:
                    if response.status != 200:
                        raise HTTPException(status_code=400, detail="Failed to download file from URL")
                    file_data = await response.read()
        
        elif message.file.startswith("data:"):
            try:
                # Handle data URI format
                file_base64 = message.file.split(",")[1]
                file_data = base64.b64decode(file_base64)
            except IndexError:
                raise HTTPException(status_code=400, detail="Invalid data URI format")
            except Exception:
                raise HTTPException(status_code=400, detail="Failed to decode base64 file")
        
        else:
            # Assume it's a base64 string
            try:
                file_data = base64.b64decode(message.file)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid base64 file")
        
        # Create options for the document
        options = {}
        if message.caption:
            options["caption"] = message.caption

        chat_id = get_chat_id_by_phone_number(message.chat_id)
        if chat_id is None:
            chat_id = message.chat_id
            
        # Send the document
        await bot.send_document(
            chat_id=chat_id, 
            document=file_data, 
            filename=filename,
            **options
        )
            
        log_info(f"File sent to {chat_id} ({filename})", 'info')
    except Exception as e:
        log_info(f"Error in sending file {filename} to {chat_id}", 'error')
        raise e