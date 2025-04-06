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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="Message Processing Service")

# Environment variables
API_PORT = int(os.getenv("API_PORT", 8001))
# Ensure DATA_SERVICE_URL points to the base URL of your Next.js app (e.g., http://localhost:3000)
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:3000")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://127.0.0.1:6325/v1/chat/completions")

# --- Input Model ---
class NewMessageRequest(BaseModel):
    message_id: str # The unique ID for the message
    source_name: str
    chat_id: str
    text: str
    sender_id: Optional[str] = None
    sender_name: str
    image: Optional[str] = None
    # We don't expect 'data' in the initial request to this service

# --- Model for sending data TO the data service ---
# This matches the expected structure of the /api/chats/new_message endpoint
class DataServicePayload(BaseModel):
    message_id: str
    source_name: str
    chat_id: str
    text: str
    sender_id: Optional[str] = None
    sender_name: str
    image: Optional[str] = None
    data: Optional[Dict[str, Any]] = None # LLM classification goes here in the second call

# --- LLM Processing Function (mostly unchanged) ---
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

    default_classification = {
        "message_type": "",
        "field": "",
        "incident": ""
    }

    try:
        payload = {
            "model": "mist", # Or your desired model
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "stream": True # Assuming your LLM service supports streaming for potentially faster responses
        }

        result = ""
        logger.info(f"Sending request to LLM: {LLM_SERVICE_URL}")
        async with aiohttp.ClientSession() as session:
            async with session.post(LLM_SERVICE_URL, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error from LLM service: {response.status} - {error_text}")
                    # Don't raise HTTPException here, return default
                    return default_classification

                # Process stream response chunk by chunk
                async for chunk in response.content:
                    chunk_text = chunk.decode('utf-8').strip()
                    # Handle potential server-sent event format
                    if chunk_text.startswith("data: "):
                        json_str = chunk_text[len("data: "):].strip()
                        if json_str == "[DONE]":
                            break
                        try:
                            data = json.loads(json_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta and delta["content"] is not None:
                                    result += delta["content"]
                        except json.JSONDecodeError:
                            logger.warning(f"Could not decode LLM stream chunk as JSON: {json_str}")
                            continue # Skip malformed chunks
                    elif chunk_text: # Handle non-SSE streaming if necessary
                         logger.warning(f"Received unexpected non-SSE chunk: {chunk_text}")
                         # Attempt to append if it looks like part of the JSON
                         result += chunk_text


        logger.info(f"Raw LLM Result: {result}")

        # Parse the accumulated result as JSON
        try:
            # Clean the result string
            result = result.strip()
            # Remove potential markdown code fences
            if result.startswith("```json"):
                result = result[7:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip() # Strip again after removing fences

            if not result:
                 logger.warning("LLM returned empty result string.")
                 return default_classification

            result_json = json.loads(result)
            # Basic validation (optional but recommended)
            if not all(k in result_json for k in default_classification.keys()):
                logger.warning(f"LLM JSON missing expected keys. Got: {result_json.keys()}")
                # You could try to merge or just return default
                # return {**default_classification, **result_json} # Merge approach
                return default_classification # Safer approach

            logger.info(f"Successfully parsed LLM classification: {result_json}")
            return result_json
        except json.JSONDecodeError:
            logger.error(f"Failed to parse final LLM response as JSON: {result}")
            return default_classification
        except Exception as e:
             logger.error(f"Unexpected error parsing LLM result: {traceback.format_exc()}")
             return default_classification

    except aiohttp.ClientError as e:
        logger.error(f"HTTP Client Error connecting to LLM: {str(e)}")
        return default_classification
    except Exception as e:
        logger.error(f"Error processing with LLM: {traceback.format_exc()}")
        return default_classification

# --- Function to send data to the Data Service's new_message endpoint ---
async def send_to_data_service_new_message(payload: DataServicePayload):
    """Sends data to the Data Service /api/chats/new_message endpoint."""
    url = f"{DATA_SERVICE_URL}/api/chats/new_message"
    try:
        # Use .model_dump() for Pydantic v2+ or .dict() for v1
        # Exclude None values so optional fields aren't sent as null unless explicitly set
        payload_dict = payload.model_dump(exclude_none=True) if hasattr(payload, 'model_dump') else payload.dict(exclude_none=True)

        # Determine if this is an update call (contains 'data') for logging
        log_prefix = "Forwarding initial" if payload.data is None else "Sending LLM update for"
        logger.info(f"{log_prefix} message to Data Service: {url} for message {payload.message_id}")
        # logger.debug(f"Payload being sent: {json.dumps(payload_dict, indent=2)}") # Uncomment for detailed debugging

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

# --- Background Task for LLM Processing and Update ---
async def process_and_update_in_background(message_data: NewMessageRequest):
    """Processes message with LLM and sends update to Data Service."""
    logger.info(f"[Background Task] Starting LLM processing for message {message_data.message_id}")

    # 1. Process with LLM
    classification_data = await process_with_llm(message_data.text)
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
        data=classification_data # Add the classification data here
    )

    # 3. Send the update to the data service
    success = await send_to_data_service_new_message(update_payload)

    if success:
        logger.info(f"[Background Task] Successfully sent LLM update to Data Service for message {message_data.message_id}")
    else:
        logger.error(f"[Background Task] Failed to send LLM update to Data Service for message {message_data.message_id}")
    # No return value needed for background task

# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    """Initialize the service on startup"""
    # load_config_from_data_service() # Keep if needed, but commented out as per original code
    logger.info("Message Processing Service started.")
    logger.info(f"Data Service URL: {DATA_SERVICE_URL}")
    logger.info(f"LLM Service URL: {LLM_SERVICE_URL}")


# Removed /update endpoint as it wasn't used and load_config was commented out

@app.post("/new_message")
async def new_message(message: NewMessageRequest, background_tasks: BackgroundTasks):
    """
    Receives a new message, forwards it immediately to the data service,
    and then processes it with LLM in the background, sending an update.
    """
    logger.info(f"Received new message: ID {message.message_id} from {message.source_name}, chat_id: {message.chat_id}")

    # 1. Prepare the initial payload (without LLM data)
    initial_payload = DataServicePayload(
        message_id=message.message_id,
        source_name=message.source_name,
        chat_id=message.chat_id,
        text=message.text,
        sender_id=message.sender_id,
        sender_name=message.sender_name,
        image=message.image,
        data=None # Explicitly None for the first call
    )

    # 2. Immediately forward the initial message to the data service
    # We await this to ensure the message is at least registered before confirming receipt
    forward_success = await send_to_data_service_new_message(initial_payload)

    if not forward_success:
        # If the initial forwarding fails, we cannot proceed reliably.
        logger.error(f"CRITICAL: Failed to forward initial message {message.message_id} to Data Service. Aborting further processing.")
        raise HTTPException(status_code=502, detail="Failed to forward message to data service")

    # 3. Add the LLM processing and subsequent update to background tasks
    # Pass the original incoming message data to the background task
    background_tasks.add_task(process_and_update_in_background, message)
    logger.info(f"Scheduled background LLM processing for message {message.message_id}")

    # 4. Return immediate success response to the caller
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