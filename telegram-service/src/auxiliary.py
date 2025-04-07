import aiohttp
import logging
from src.config import data_service_url, message_handler_url
from src.schemas import MessagePayload, ChatRegistrationSchema
import base64

logger = logging.getLogger(__name__)

async def get_active_chats() -> list[str]:
    logger.info(f"Fetching active chats from {data_service_url}")
    url = f"{data_service_url}/get_active_chats?source_name=telegram"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                active_chats = data.get("active_chats", [])
                logger.info(f"Fetched active chats")
                return active_chats
            else:
                raise Exception(f"Failed to fetch active chats, status code: {response.status}")


async def get_telegram_api_key() -> str:
    logger.info(f"Fetching telegram API key from {data_service_url}")
    #MOCK
    return "7667447561:AAGBrVzUNsGOdgVohYyiqOSf1P6EM6H4M-8"
    #MOCK
    url = f"{data_service_url}/get_telegram_api_key?source_name=telegram"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                telegram_api_key = data.get("telegram_api_key")
                if telegram_api_key:
                    logger.info(f"Fetched telegram API key")
                    return telegram_api_key
                raise Exception("telegram_api_key not found in response.")
            else:
                raise Exception(f"Failed to fetch telegram API key, status code: {response.status}")
            

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


async def unregister_chat(chat_id: int) -> None:
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