import aiohttp
import logging
from src.config import MESSENGER_API_SERVICE_URL
from src.schemas import MessagePayload, ChatRegistrationSchema
import base64

logger = logging.getLogger(__name__)

async def register_chat(chat_registration: ChatRegistrationSchema) -> None:
    logger.info(f"Registering chat {chat_registration.chat_id} with name {chat_registration.chat_name}")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{MESSENGER_API_SERVICE_URL}/chats", 
            json=chat_registration.model_dump()
        ) as response:
            if response.status != 200:
                logger.error(f"Failed to register chat, status code: {response.status}")
            else:
                logger.info("Chat registered successfully.")


async def unregister_chat(chat_id: str) -> None:
    logger.info(f"Unregistering chat {chat_id}")
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{MESSENGER_API_SERVICE_URL}/chats/{chat_id}") as resp:
            if resp.status == 200:
                logger.info(f"Chat unregistered successfully: {chat_id}")
            else:
                logger.error(f"Failed to unregister chat {chat_id}, status: {resp.status}")


async def send_new_message(message: MessagePayload) -> None:
    logger.info(f"Sending new message: {message}")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{MESSENGER_API_SERVICE_URL}/new_message", 
            json=message.model_dump()
        ) as response:
            if response.status != 200:
                logger.error(f"Failed to forward message, status code: {response.status}")
            else:
                logger.info("Message forwarded successfully.")


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