import aiohttp
from src.config import MESSENGER_API_SERVICE_URL, BACKEND_SERVICE_URL, logger
from src.schemas import MessagePayload, ChatRegistrationSchema
import base64
import httpx
from src.schemas import LogSchema
from typing import Literal

def log_info(message: str, level: Literal['info', 'error', 'warning']):
    if level == 'info':
        logger.info(message)
    elif level == 'error':
        logger.error(message)
    elif level == 'warning':
        logger.warning(message)

    with httpx.Client() as client:
        try:
            client.post(
                f"{BACKEND_SERVICE_URL}/logs",
                json=LogSchema(message=message, level=level).model_dump()
            )
        except Exception as e:
            logger.error(f"Failed to send log to backend service: {e}")

async def register_chat(chat_registration: ChatRegistrationSchema) -> None:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{MESSENGER_API_SERVICE_URL}/chats", 
            json=chat_registration.model_dump()
        ) as response:
            if response.status != 200:
                log_info(f"Failed to register chat, status code: {response.status}", 'error')
            else:
                log_info("Chat registered successfully.", 'info')


async def unregister_chat(chat_id: str) -> None:
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{MESSENGER_API_SERVICE_URL}/chats/{chat_id}") as resp:
            if resp.status == 200:
                log_info(f"Chat unregistered successfully: {chat_id}", 'info')
            else:
                log_info(f"Failed to unregister chat {chat_id}, status: {resp.status}", 'error')


async def send_new_message(message: MessagePayload) -> None:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{MESSENGER_API_SERVICE_URL}/api/llm_processing", 
            json=message.model_dump()
        ):
            pass


async def get_blob_photo(photo) -> str | None:
    if not photo:
        return None
    
    # Get the highest resolution photo
    photo_file = await photo[-1].get_file()
    # Download photo as byte array
    image_bytes = await photo_file.download_as_bytearray()
    # Encode the image in base64
    image_blob = base64.b64encode(image_bytes).decode('utf-8')
    return image_blob


async def get_blob_voice(voice) -> str | None:
    if not voice:
        return None
    
    # Get the voice file
    voice_file = await voice.get_file()
    # Download voice as byte array
    voice_bytes = await voice_file.download_as_bytearray()
    # Encode the voice in base64
    voice_blob = base64.b64encode(voice_bytes).decode('utf-8')
    return voice_blob