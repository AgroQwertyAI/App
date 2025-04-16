import os
import json
import logging
import asyncio
import aiohttp
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import traceback # For logging

from whisper import transcribe_audio
from agent import Agent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="Message Processing Service")

agents = {}

# Environment variables
API_PORT = int(os.getenv("API_PORT", 8001))
# Ensure FILE_SERVICE_URL points to the base URL of your Next.js app (e.g., http://localhost:3000)
FILE_SERVICE_URL = os.getenv("FILE_SERVICE_URL", "http://localhost:3000")
LLM_SERVICE_URL = os.environ["LLM_SERVICE_URL"]

# --- Input Model ---
class NewMessageRequest(BaseModel):
    message_id: str # The unique ID for the message
    source_name: str
    chat_id: str
    text: str
    sender_id: Optional[str] = None
    sender_name: str
    image: Optional[str] = None
    is_private: Optional[bool] = False
    voice: Optional[str] = None
    # We don't expect 'data' in the initial request to this service

# --- Model for sending data TO the data service ---
# This matches the expected structure of the /api/chats/new_message endpoint


async def is_monitoring(chat_id: str) -> bool:
    """
    Checks if a chat should be monitored by querying the Data Service.
    Returns True if the chat is active and should be monitored, False otherwise.
    """
    url = f"{FILE_SERVICE_URL}/api/chats/{chat_id}"
    try:
        logger.info(f"Checking monitoring status for chat: {chat_id}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    chat_data = await response.json()
                    is_active = chat_data.get('active', False)
                    logger.info(f"Chat {chat_id} active status: {is_active}")
                    return is_active
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to fetch chat status for {chat_id}: {response.status} - {error_text}")
                    return True  # Default to not monitoring if we can't fetch status
    except aiohttp.ClientError as e:
        logger.error(f"HTTP Client Error fetching chat status for {chat_id}: {str(e)}")
        return True
    except Exception as e:
        logger.error(f"Error checking monitoring status for chat {chat_id}: {traceback.format_exc()}")
        return True
# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    """Initialize the service on startup"""
    # load_config_from_data_service() # Keep if needed, but commented out as per original code
    logger.info("Message Processing Service started.")
    logger.info(f"Data Service URL: {FILE_SERVICE_URL}")
    logger.info(f"LLM Service URL: {LLM_SERVICE_URL}")


# Removed /update endpoint as it wasn't used and load_config was commented out

@app.post("/new_message")
async def new_message(message: NewMessageRequest, background_tasks: BackgroundTasks):
    """
    Receives a new message, forwards it immediately to the data service,
    and then processes it with LLM in the background, sending an update.
    """
    logger.info(f"Received new message: ID {message.message_id} from {message.source_name}, chat_id: {message.chat_id}")

    if message.voice:
        message.text = transcribe_audio(message.voice)
        print(message.text)
    
    
    if not message.is_private and not await is_monitoring(message.chat_id)  :
        logger.info(f"Chat {message.chat_id} is not active. Skipping processing.")
        return {"status": "chat_not_active"}

    if message.sender_id not in agents:
        logger.info(f"Creating new agent for sender: {message.sender_id}")
        agents[message.sender_id] = Agent(message.sender_id)
    
    agent = agents[message.sender_id]
    background_tasks.add_task(agent.process_message, message)
    
    return {
        "status": "received_processing_started",
        "message_id": message.message_id
    }

# --- Main Execution ---
def main():
    import uvicorn
    logger.info(f"Starting Message Processing Service on port {API_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)

if __name__ == "__main__":
    main()