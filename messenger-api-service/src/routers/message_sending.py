from fastapi import APIRouter
from src.schemas.endpoints.message import MessagePayloadPost
from telegram import Bot
from src.config import TELEGRAM_BOT_TOKEN
import base64
import logging

message_sending_router = APIRouter(tags=["Message Sending"])

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@message_sending_router.post(
    "/telegram_message/{telegram_chat_id}",
    status_code=200,
    response_model=None,
    description="Send message to telegram private chat specified by telegram chat id"
)
async def send_message(telegram_chat_id: str, payload: MessagePayloadPost):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Send text message
    if payload.text:
        await bot.send_message(chat_id=telegram_chat_id, text=payload.text)
    
    # If a file is provided in base64 format, decode and send it
    if payload.base64_file:
        try:
            file_bytes = base64.b64decode(payload.base64_file)
            
            # Send as a document with the specified MIME type
            if payload.document_mime_type == "xlsx":
                filename = f"document.{payload.document_mime_type}"
                await bot.send_document(
                    chat_id=telegram_chat_id, 
                    document=file_bytes, 
                    filename=filename
                )

                logger.info(f"File sent to telegram chat {telegram_chat_id}")
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            raise


@message_sending_router.post("/whatsapp_message/{whatsapp_chat_id}",
    status_code=200,
    response_model=None,
    description="Send message to whatsapp private chat specified by whatsapp chat id"
)
async def send_message(whatsapp_chat_id: str, payload: MessagePayloadPost):
    pass