import os
import json
import logging
import asyncio
import aiohttp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="Message Processing Service")

# Environment variables
API_PORT = int(os.getenv("API_PORT", 8000))
DATA_SERVICE_HOST = os.getenv("DATA_SERVICE_HOST", "localhost")
DATA_SERVICE_PORT = int(os.getenv("DATA_SERVICE_PORT", 8001))
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://127.0.0.1:6325/v1/chat/completions")

# Service configuration
config = {}

class NewMessageRequest(BaseModel):
    source_name: str
    chat_id: str
    text: str
    sender_id: str
    sender_name: str
    image: Optional[str] = None

class MessageData(BaseModel):
    sender: str
    text: str
    type: str
    data: Dict[str, Any]

class ProcessedMessageSubmit(BaseModel):
    chat_id: str
    source_name: str
    message: MessageData

async def load_config_from_data_service():
    """Load configuration from the data service"""
    pass
    #try:
        #url = f"http://{DATA_SERVICE_HOST}:{DATA_SERVICE_PORT}/get_config"
        #async with aiohttp.ClientSession() as session:
        #    async with session.get(url) as response:
        #        if response.status == 200:
        #            config.update(await response.json())
        #            logger.info("Successfully loaded configuration from data service")
        #        else:
        #            logger.error(f"Failed to load config: {response.status}")
    #except Exception as e:
    #    logger.error(f"Error loading config: {str(e)}")

async def process_with_llm(text: str) -> Dict[str, Any]:
    """Process text with LLM and return the classification"""
    system_prompt = """You are an AI assistant that analyzes messages.
    Analyze the message and classify it according to the following format.
    Respond ONLY with a valid JSON object in this format and nothing else:
    {
        "message_type": "",
        "field": "",
        "incident": ""
    }
    All fields can be empty if no relevant information is present in the message."""
    
    try:
        payload = {
            "model": "mist",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "stream": True
        }
        
        result = ""
        async with aiohttp.ClientSession() as session:
            async with session.post(LLM_SERVICE_URL, json=payload) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail="Error from LLM service")
                
                # Process stream response chunk by chunk
                async for chunk in response.content:
                    chunk_text = chunk.decode('utf-8').strip()
                    if chunk_text.startswith("data: ") and not chunk_text.endswith("[DONE]"):
                        try:
                            json_str = chunk_text[6:]  # Remove "data: " prefix
                            data = json.loads(json_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta and delta["content"] is not None:
                                    result += delta["content"]
                        except json.JSONDecodeError:
                            continue
        
        # Parse the result as JSON
        try:
            # Clean the result string to ensure it contains only valid JSON
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.endswith("```"):
                result = result[:-3]
            
            result_json = json.loads(result.strip())
            return result_json
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response as JSON: {result}")
            return {
                "message_type": "",
                "field": "",
                "incident": ""
            }
    except Exception as e:
        logger.error(f"Error processing with LLM: {str(e)}")
        return {
            "message_type": "",
            "field": "",
            "incident": ""
        }

async def submit_processed_message(processed: ProcessedMessageSubmit):
    """Submit processed message to the data service"""
    try:
        url = f"http://{DATA_SERVICE_HOST}:{DATA_SERVICE_PORT}/submit_processed_message"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=processed.dict()) as response:
                if response.status != 200:
                    logger.error(f"Failed to submit processed message: {response.status}")
                    return False
                return True
    except Exception as e:
        logger.error(f"Error submitting processed message: {str(e)}")
        return False

@app.on_event("startup")
async def startup_event():
    """Initialize the service on startup"""
    await load_config_from_data_service()

@app.post("/update")
async def update_config():
    """Update configuration from data service"""
    await load_config_from_data_service()
    return {"message": "Configuration updated successfully"}

@app.post("/new_message")
async def new_message(message: NewMessageRequest):
    """Process new message with LLM"""
    logger.info(f"Received new message from {message.source_name}, chat_id: {message.chat_id}")
    
    # Process message with LLM
    message_content = message.text
    if message.image:
        message_content += f"\n[Image content: {message.image}]"
    
    classification = await process_with_llm(message_content)
    
    # Create processed message
    processed = ProcessedMessageSubmit(
        chat_id=message.chat_id,
        source_name=message.source_name,
        message=MessageData(
            sender=message.sender_name,
            text=message.text,
            type="user_message",
            data=classification
        )
    )
    
    # Submit processed message
    success = await submit_processed_message(processed)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to submit processed message")
    
    return {"message": "Message processed successfully", "classification": classification}

def main():
    import uvicorn
    logger.info(f"Starting Message Processing Service on port {API_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)

if __name__ == "__main__":
    main()