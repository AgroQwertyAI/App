import logging
import os
import json
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import aiohttp
import traceback  # For logging
from settings import get_template_by_id, get_template_id

from data_lists import CULTURES, DIVISIONS, OPERATIONS

from scenario import (
    extract_data_from_message,
    is_report,
    agentic,
    get_history_for_followup,
    determine_questions,
)
from util import dict_to_csv_string, generate_table_image, extract_questions, parse_table_from_message

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Environment variables
API_PORT = int(os.getenv("API_PORT", 8001))
FILE_SERVICE_URL = os.environ["FILE_SERVICE_URL"]
LLM_SERVICE_URL = os.environ["LLM_SERVICE_URL"]
WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://localhost:52101")
SAVE_SERVICE_URL = os.getenv("SAVE_SERVICE_URL", "http://localhost:52001")

# Path to store failed attempts
FAILED_LIST_PATH = "failed_list.json"

class DataServicePayload(BaseModel):
    message_id: str
    source_name: str
    chat_id: str
    text: str
    sender_id: Optional[str] = None
    sender_name: str
    image: Optional[str] = None
    data: Optional[List[Any]] = None
    is_private: Optional[bool] = False

class NewMessageRequest(BaseModel):
    message_id: str
    source_name: str
    chat_id: str
    text: str
    sender_id: Optional[str] = None
    sender_name: str
    image: Optional[str] = None
    is_private: Optional[bool] = False
    voice: Optional[str] = None
    datetime : Optional[str] = None

class Images(BaseModel):
    images: List[str] = []

class SaveServicePayload(BaseModel):
    sender_phone_number: str
    sender_name: str
    sender_id: str
    original_message_text: str
    formatted_message_text: Dict[str, List[Any]]
    images: Images = Field(default_factory=lambda: Images(images=[]))
    extra: Dict[str, Any] = Field(default_factory=dict)

class Agent:
    def __init__(self, user):
        self.state = "NONE"
        self.user = user
        self.history = []
        self.original_report_message = None

    async def process_chat_message(self, message):
        await self.process_and_update_in_background(message)
        logger.info(f"Scheduled background LLM processing for message {message.message_id}")

    async def process_message(self, message):
        if not message.is_private:
            if await is_report(message.text):
                initial_payload = DataServicePayload(
                    message_id=message.message_id,
                    source_name=message.source_name,
                    chat_id=message.chat_id,
                    text=message.text,
                    sender_id=message.sender_id,
                    sender_name=message.sender_name,
                    image=message.image,
                    data=None,
                    is_private=message.is_private,
                )
                await self.send_to_data_service_new_message(initial_payload)
                await self.process_chat_message(message)
        else:
            if self.state == "FOLLOW_UP":
                result = await agentic(self.history, message.text)
                self.history = result["history"]
                answer = result["answer"]
                table = parse_table_from_message(answer)
                if len(table) > 0:
                    self.state = "NONE"
                    update_payload = DataServicePayload(
                        message_id=self.original_report_message.message_id,
                        source_name=self.original_report_message.source_name,
                        chat_id=self.original_report_message.chat_id,
                        text=self.original_report_message.text,
                        sender_id=self.original_report_message.sender_id,
                        sender_name=self.original_report_message.sender_name,
                        image=self.original_report_message.image,
                        data=table,
                        is_private=self.original_report_message.is_private,
                    )
                    await self.send_to_data_service_new_message(update_payload)
                    await self.direct_message("Спасибо, ваш отчёт был записан!")
                else:
                    await self.direct_message(answer)
            else:
                if await is_report(message.text):
                    initial_payload = DataServicePayload(
                        message_id=message.message_id,
                        source_name=message.source_name,
                        chat_id=message.chat_id,
                        text=message.text,
                        sender_id=message.sender_id,
                        sender_name=message.sender_name,
                        image=message.image,
                        data=None,
                        is_private=message.is_private,
                    )
                    await self.send_to_data_service_new_message(initial_payload)
                    await self.process_chat_message(message)
                else:
                    result = await agentic(self.history, message.text)
                    self.history = result["history"]
                    await self.direct_message(result["answer"])

    async def direct_message(self, text):
        url = f"{WHATSAPP_SERVICE_URL}/send_message"
        try:
            payload = {"user": self.user, "text": text}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"Failed to send WhatsApp message to {self.user}: {response.status}")
                        return False
        except Exception:
            logger.error(f"Error sending WhatsApp message to {self.user}: {traceback.format_exc()}")
            return False

    async def direct_image(self, image):
        url = f"{WHATSAPP_SERVICE_URL}/send_image"
        try:
            payload = {"user": self.user, "image": image}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"Failed to send image to {self.user}: {response.status}")
                        return False
        except Exception:
            logger.error(f"Error sending WhatsApp image to {self.user}: {traceback.format_exc()}")
            return False

    async def send_to_data_service_new_message(self, payload: DataServicePayload):
        url = f"{FILE_SERVICE_URL}/api/chats/new_message"
        try:
            payload_dict = payload.model_dump(exclude_none=True) if hasattr(payload, 'model_dump') else payload.dict(exclude_none=True)
            log_prefix = "Forwarding initial" if payload.data is None else "Sending LLM update for"
            logger.info(f"{log_prefix} message to Data Service for message {payload.message_id}")
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload_dict) as response:
                    if response.status in (200, 201):
                        return True
                    else:
                        logger.error(f"Failed to send data to Data Service for message {payload.message_id}: {response.status}")
                        return False
        except Exception:
            logger.error(f"Error sending data to Data Service for message {payload.message_id}: {traceback.format_exc()}")
            return False

    async def process_and_update_in_background(self, message: NewMessageRequest):
        logger.info(f"[Background Task] Starting LLM processing for message {message.message_id}")
        await self.process_report(message)

    async def process_report(self, message: NewMessageRequest) -> Dict[str, Any]:
        try:
            template = get_template_by_id(await get_template_id(message.chat_id))
            result: List[Dict[str, Any]] = await extract_data_from_message(message.text, template)
            parsed_rows = []
            success = True
            for row in result:
                if row.get('success'):
                    parsed_rows.append(row['data'][0])
                    data_row = row['data'][0]
                    required_fields = ['Подразделение', 'Операция', 'Культура', 'За день, га', 'С начала операции, га']
                    if any(not data_row.get(f) for f in required_fields):
                        success = False
                else:
                    success = False

            # Add current date for empty Дата fields
            from datetime import datetime
            current_date = datetime.now().strftime('%d.%m')  # Format: DD.MM
            for row in parsed_rows:
                if not row.get('Дата'):
                    row['Дата'] = current_date

                # if row.get('Операция') and row['Операция'] not in OPERATIONS:
                #     row['Операция'] = f"{row['Операция']}*"
                # 
                # if row.get('Культура') and row['Культура'] not in CULTURES:
                #     row['Культура'] = f"{row['Культура']}*"
                # 
                # if row.get('Подразделение') and row['Подразделение'] not in DIVISIONS:
                #     row['Подразделение'] = f"{row['Подразделение']}*"

            update_payload = DataServicePayload(
                message_id=message.message_id,
                source_name=message.source_name,
                chat_id=message.chat_id,
                text=message.text,
                sender_id=message.sender_id,
                sender_name=message.sender_name,
                image=message.image,
                data=parsed_rows,
                is_private=message.is_private,
            )
            data_service_success = await self.send_to_data_service_new_message(update_payload)
            save_service_success = await self.send_to_save_service(message, parsed_rows)
            if data_service_success:
                logger.info(f"Successfully sent LLM update for message {message.message_id}")
            if save_service_success:
                logger.info(f"Successfully sent data to Save Service for message {message.message_id}")

            if success:
                pass
            else:
                # Record failed attempt
                try:
                    if os.path.exists(FAILED_LIST_PATH):
                        with open(FAILED_LIST_PATH, 'r', encoding='utf-8') as f:
                            failed_list = json.load(f)
                    else:
                        failed_list = []
                    failed_list.append({
                        'message_id': message.message_id,
                        'text': message.text,
                        'result': result,
                    })
                    with open(FAILED_LIST_PATH, 'w', encoding='utf-8') as f:
                        json.dump(failed_list, f, ensure_ascii=False, indent=2)
                except Exception:
                    logger.error(f"Error saving failed attempt: {traceback.format_exc()}")

                await self.ask_for_follow_up(message, result)
        except Exception:
            logger.error(f"Error processing with LLM: {traceback.format_exc()}")
            return {}

    async def send_to_save_service(self, message: NewMessageRequest, data: List[Dict[str, Any]], setting_id: int = 1):
        url = f"{SAVE_SERVICE_URL}/api/setting/{setting_id}/message_pending"
        try:
            template_id = await get_template_id(message.chat_id)
            template = get_template_by_id(template_id)
            cols = template["columns"]
            formatted_message_text = {col: [] for col in cols}
            row_count = len(data)
            for row in data:
                for col in cols:
                    formatted_message_text[col].append(row.get(col, ''))
            for col, values in formatted_message_text.items():
                if len(values) != row_count:
                    while len(values) < row_count:
                        values.append('')
            payload = {
                "sender_phone_number": self.user,
                "sender_name": message.sender_name,
                "sender_id": message.sender_id or "",
                "original_message_text": message.text,
                "formatted_message_text": formatted_message_text,
                "images": {"images": [] if not message.image else [message.image]},
                "extra": {"testing": True, "datetime" : message.datetime},
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    return response.status in (200, 201)
        except Exception:
            logger.error(f"Error sending data to Save Service for message {message.message_id}: {traceback.format_exc()}")
            return False

    async def ask_for_follow_up(self, message: NewMessageRequest, result: Any) -> Dict[str, Any]:
        self.state = "FOLLOW_UP"
        self.original_report_message = message
        table_image_url = generate_table_image(result)
        table_csv = dict_to_csv_string(result)
        questions = await determine_questions(table_csv)
        await self.direct_message("Добрый день! Я обработал ваш недавний отчёт, но возникли некоторые трудности.")
        if table_image_url:
            await self.direct_image(table_image_url)
        if questions:
            await self.direct_message("У меня есть несколько вопросов по вашему отчёту:")
            await self.direct_message(questions)
        else:
            await self.direct_message("Я не смог выделить из него каких-либо данных. Пожалуйста, пришлите отчёт заново в стандартном формате. Если вы не отправляли никаких сообщений, просто игнорируйте это сообщение.")
        self.history = await get_history_for_followup(table_csv, questions)
        return {"status": "follow-up-requested"}
