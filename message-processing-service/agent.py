import logging
import os
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import aiohttp
import traceback # For logging

from scenario import extract_data_from_message, is_report, agentic

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

        print("MESSAGE_DATA", message_data)
        # 1. Process with LLM
        classification_data = await self.process_report(message_data.text)
        logger.info(f"[Background Task] LLM processing complete for message {message_data.message_id}. Result: {classification_data}")

        # 2. Prepare payload for the update call (including LLM data)
        update_payload = DataServicePayload(
            message_id=message_data.message_id,
            source_name=message_data.source_name,
            chat_id=message_data.chat_id,
            text=message_data.text,
            sender_id=message_data.sender_id,
            sender_name=message_data.sender_name,
            image=message_data.image,
            data=classification_data,
            is_private=message_data.is_private
        )

        # 3. Send the update to the data service
        success = await self.send_to_data_service_new_message(update_payload)

        if success:
            logger.info(f"[Background Task] Successfully sent LLM update to Data Service for message {message_data.message_id}")
        else:
            logger.error(f"[Background Task] Failed to send LLM update to Data Service for message {message_data.message_id}")
        # No return value needed for background task
        
    # --- LLM Processing Function (mostly unchanged) ---
    async def process_report(self, text: str) -> Dict[str, Any]:
        
        try:
            logger.info(f"Sending request to LLM: {LLM_SERVICE_URL}")

            result = await extract_data_from_message(text)    

            return result['data'] if result['success'] else []



        except aiohttp.ClientError as e:
            logger.error(f"HTTP Client Error connecting to LLM: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Error processing with LLM: {traceback.format_exc()}")
            return {}