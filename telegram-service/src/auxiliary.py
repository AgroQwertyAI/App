import aiohttp
import logging
from src.config import data_service_url, message_handler_url
from src.schemas import MessagePayload, ChatRegistrationSchema
import base64

logger = logging.getLogger(__name__)

async def get_active_chats() -> list[str]:
    logger.info(f"Fetching active chats from {data_service_url}")
    url = f"{data_service_url}/api/chats?source_name=telegram"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                chats = data.get("chats", [])
                # Filter to only include active chats and extract chat IDs
                active_chats = [str(chat["chat_id"]) for chat in chats if chat.get("active", False)]
                logger.info(f"Fetched {len(active_chats)} active chats")
                return active_chats
            else:
                raise Exception(f"Failed to fetch active chats, status code: {response.status}")
            

async def register_chat(chat_registration: ChatRegistrationSchema) -> None:
    logger.info(f"Registering chat {chat_registration.chat_id} with name {chat_registration.chat_name}")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{data_service_url}/api/chats", 
            json=chat_registration.model_dump()
        ) as response:
            if response.status != 200:
                logger.error(f"Failed to register chat, status code: {response.status}")
            else:
                logger.info("Chat registered successfully.")


async def unregister_chat(chat_id: str) -> None:
    logger.info(f"Unregistering chat {chat_id}")
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{data_service_url}/api/chats/{chat_id}") as resp:
            if resp.status == 200:
                logger.info(f"Chat unregistered successfully: {chat_id}")
            else:
                logger.error(f"Failed to unregister chat {chat_id}, status: {resp.status}")


async def send_new_message(message: MessagePayload) -> None:
    logger.info(f"Sending new message: {message}")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{message_handler_url}/new_message", 
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


async def get_blob_video(video) -> str | None:
    if not video:
        return None
    
    # Get the video file
    video_file = await video.get_file()
    # Download video as byte array
    video_bytes = await video_file.download_as_bytearray()
    # Encode the video in base64
    video_blob = base64.b64encode(video_bytes).decode('utf-8')
    return video_blob


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