import logging
import os
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import aiohttp
import traceback # For logging
from settings import get_template_by_id, get_template_id

from scenario import extract_data_from_message, is_report, agentic, get_history_for_followup
from util import dict_to_csv_string, generate_table_image, extract_questions, parse_table_from_message


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Environment variables
API_PORT = int(os.getenv("API_PORT", 8001))
# Ensure DATA_SERVICE_URL points to the base URL of your Next.js app (e.g., http://localhost:3000)
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:3000")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://127.0.0.1:6325/v1/chat/completions")
WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://localhost:52101")

class DataServicePayload(BaseModel):
    message_id: str
    source_name: str
    chat_id: str
    text: str
    sender_id: Optional[str] = None
    sender_name: str
    image: Optional[str] = None
    data: Optional[list[Any]] = None # LLM classification goes here in the second call
    is_private: Optional[bool] = False

class NewMessageRequest(BaseModel):
    message_id: str # The unique ID for the message
    source_name: str
    chat_id: str
    text: str
    sender_id: Optional[str] = None
    sender_name: str
    image: Optional[str] = None
    is_private: Optional[bool] = False

class Agent:
    
    def __init__(self, user):
        self.state = "NONE"
        self.user = user
        self.history = []
        
    
    async def process_chat_message(self, message):
        
        
        await self.process_and_update_in_background(message)
        logger.info(f"Scheduled background LLM processing for message {message.message_id}")
        
        
    
    
    async def process_message(self, message):
        
        if not message.is_private:
            initial_payload = DataServicePayload(
                    message_id=message.message_id,
                    source_name=message.source_name,
                    chat_id=message.chat_id,
                    text=message.text,
                    sender_id=message.sender_id,
                    sender_name=message.sender_name,
                    image=message.image,
                    data=None, # Explicitly None for the first call
                    is_private=message.is_private
                )
                
            await self.send_to_data_service_new_message(initial_payload)
            
            
            await self.process_chat_message(message)
            
            
        else:
            if self.state == "FOLLOW_UP":
                result = await agentic(self.history, message.text)
                self.history = result["history"]
                answer = result["answer"]
                
                print(result)
                
                table = parse_table_from_message(answer)
                
                if len(table) > 0:
                    self.state = "NONE"
                    
                    # 2. Prepare payload for the update call (including LLM data)
                    update_payload = DataServicePayload(
                        message_id=message.message_id,
                        source_name=message.source_name,
                        chat_id=message.chat_id,
                        text=message.text,
                        sender_id=message.sender_id,
                        sender_name=message.sender_name,
                        image=message.image,
                        data=table,
                        is_private=message.is_private
                    )

                    # 3. Send the update to the data service
                    success = await self.send_to_data_service_new_message(update_payload)
                
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
                        data=None, # Explicitly None for the first call
                        is_private=message.is_private
                    )

                    await self.send_to_data_service_new_message(initial_payload)

                    await self.process_chat_message(message)
                else:
                    result = await agentic(self.history, message.text)
                    self.history = result["history"]
                    print(self.user)


                    await self.direct_message(result["answer"])
                
    async def direct_message(self, text):
        url = f"{WHATSAPP_SERVICE_URL}/send_message"
        
        try:
            payload = {
                "user": self.user,
                "text": text
            }
            
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        response_json = await response.json()
                    
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send WhatsApp message to {self.user}: {response.status} - {error_text}")
                        return False
                     
        except Exception as e:
            logger.error(f"Error sending WhatsApp message to {self.user}: {traceback.format_exc()}")
            return False
    
    async def direct_image(self, image):
        url = f"{WHATSAPP_SERVICE_URL}/send_image"
        
        try:
            payload = {
                "user": self.user,
                "image": image
            }
            
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        response_json = await response.json()
                    
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send WhatsApp message to {self.user}: {response.status} - {error_text}")
                        return False
                     
        except Exception as e:
            logger.error(f"Error sending WhatsApp message to {self.user}: {traceback.format_exc()}")
            return False

    async def send_to_data_service_new_message(self, payload: DataServicePayload):
        """Sends data to the Data Service /api/chats/new_message endpoint."""
        url = f"{DATA_SERVICE_URL}/api/chats/new_message"
        try:
            payload_dict = payload.model_dump(exclude_none=True) if hasattr(payload, 'model_dump') else payload.dict(exclude_none=True)

            log_prefix = "Forwarding initial" if payload.data is None else "Sending LLM update for"
            logger.info(f"{log_prefix} message to Data Service: {url} for message {payload.message_id}")

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload_dict) as response:
                    if response.status == 200 or response.status == 201: # Accept 200 OK or 201 Created
                        response_json = await response.json()
                        logger.info(f"Successfully sent data to Data Service for message {payload.message_id}. Response: {response_json}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send data to Data Service for message {payload.message_id}: {response.status} - {error_text}")
                        return False
        except aiohttp.ClientError as e:
             logger.error(f"HTTP Client Error sending data to Data Service for message {payload.message_id}: {str(e)}")
             return False
        except Exception as e:
            logger.error(f"Error sending data to Data Service for message {payload.message_id}: {traceback.format_exc()}")
            return False

    async def process_and_update_in_background(self, message_data: NewMessageRequest):
        """Processes message with LLM and sends update to Data Service."""
        logger.info(f"[Background Task] Starting LLM processing for message {message_data.message_id}")

        # 1. Process with LLM
        await self.process_report(message_data)
        
        # No return value needed for background task
        
    # --- LLM Processing Function (mostly unchanged) ---
    async def process_report(self, message: NewMessageRequest) -> Dict[str, Any]:
        
        try:
            logger.info(f"Sending request to LLM: {LLM_SERVICE_URL}")
            template = get_template_by_id(await get_template_id(message.chat_id))
            result :list = await extract_data_from_message(message.text, template)    
            
            parsed_rows = []
            
            success  = True
            
            questions = False
            
            for row in result:
                if row['success'] and not row['question']:
                    parsed_rows.append(row['data'][0])
                else:
                    success = False
                
                if row['question']:
                    questions = True
                    
            print(result)
            
            if success:

                # 2. Prepare payload for the update call (including LLM data)
                update_payload = DataServicePayload(
                    message_id=message.message_id,
                    source_name=message.source_name,
                    chat_id=message.chat_id,
                    text=message.text,
                    sender_id=message.sender_id,
                    sender_name=message.sender_name,
                    image=message.image,
                    data=parsed_rows,
                    is_private=message.is_private
                )

                # 3. Send the update to the data service
                success = await self.send_to_data_service_new_message(update_payload)

                if success:
                    logger.info(f"[Background Task] Successfully sent LLM update to Data Service for message {message.message_id}")
                else:
                    logger.error(f"[Background Task] Failed to send LLM update to Data Service for message {message.message_id}")
            elif questions:
                print(questions)
                
                await self.ask_for_follow_up(message, result)
                



        except aiohttp.ClientError as e:
            logger.error(f"HTTP Client Error connecting to LLM: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Error processing with LLM: {traceback.format_exc()}")
            return {}

    async def ask_for_follow_up(self, message: NewMessageRequest, result: dict) -> Dict[str, Any]:
        self.state = "FOLLOW_UP"
        
        table_image_url = generate_table_image(result)
    
        # Generate table image
        table_image_url = generate_table_image(result)

        # Extract questions if any
        questions = extract_questions(result)
        print(questions)
        table_csv = dict_to_csv_string(result)
        # Send initial message
        await self.direct_message("Добрый день! Я обработал ваш недавний отчёт, но возникли некоторые трудности.")
        
        if table_image_url:
            await self.direct_image(table_image_url)

        if questions:
            # If there are questions, ask them
            await self.direct_message("У меня есть несколько вопросов по вашему отчёту:")
            await self.direct_message(questions)
            
        else:
            await self.direct_message("Я не смог выделить из него каких-либо данных. Пожалуйста, пришлите отчёт заново в стандартном формате. Если вы не отправляли никаких сообщений, просто игнорируйте это сообщение.")
        
        self.history = await get_history_for_followup(table_csv, questions)
        
        
        return {"status": "follow-up-requested"}