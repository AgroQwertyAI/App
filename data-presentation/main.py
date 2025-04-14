import os
import locale
import logging
from typing import List, Dict, Any
from datetime import datetime

import aiohttp
import pandas as pd
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from src.models import TableRequest, ChartRequest, ChartResponse
from src.table_generators import (
    create_dataframe_from_data,
    generate_table_response,
    TableFormat
)
from src.chart_generators import generate_chart_data_from_data

# Set locale for date formatting
locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
# Logging setup, will be replaced with API
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration constants
API_PORT = int(os.getenv("API_PORT", 52003))
DATA_SERVICE_HOST = os.getenv("DATA_SERVICE_HOST", "localhost")
DATA_SERVICE_PORT = int(os.getenv("DATA_SERVICE_PORT", 3000))
DATA_SERVICE_URL = f"http://{DATA_SERVICE_HOST}:{DATA_SERVICE_PORT}"

# FastAPI initialization
app = FastAPI(
    title="Data Presentation Service",
    description="Service for generating tables and charts from processed messages",
    version="0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def fetch_data_service(url: str) -> dict:
    """Base function for data service requests."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    status_code = 502 if response.status >= 500 else response.status
                    detail = await response.text()
                    raise HTTPException(status_code=status_code,
                                        detail=f"Error requesting data service: {detail}")
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=503, detail=f"Data service is unavailable: {str(e)}")


def normalize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensures consistent message format, preserving data arrays."""
    normalized = []

    for msg in messages:
        if isinstance(msg.get('data'), list):
            # If data is already a list, keep it as is
            normalized.append(msg)
        elif isinstance(msg.get('data'), dict):
            # If data is a dict, wrap it in a list
            new_msg = {k: v for k, v in msg.items() if k != 'data'}
            new_msg['data'] = [msg['data']]
            normalized.append(new_msg)

    return normalized


async def fetch_processed_messages(chat_id: str) -> List[Dict[str, Any]]:
    url = f"{DATA_SERVICE_URL}/api/chats/messages/{chat_id}"
    data = await fetch_data_service(url)

    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Invalid data format")

    return normalize_messages(data)


def filter_messages_by_time(messages: List[Dict[str, Any]],
                            start_time: datetime,
                            end_time: datetime,
                            time_format: str) -> List[Dict[str, Any]]:
    """Filters messages by time range."""
    filtered = []

    for msg in messages:
        timestamp = msg.get('timestamp')
        if not timestamp or not isinstance(timestamp, str):
            continue

        try:
            # Handle MongoDB timestamp format
            if isinstance(timestamp, dict) and '$date' in timestamp:
                timestamp = timestamp['$date']
                
            msg_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if start_time <= msg_time <= end_time:
                if time_format:
                    msg['timestamp'] = msg_time.strftime(time_format)
                filtered.append(msg)

        except ValueError as e:
            logger.warning(f"Не удалось распарсить timestamp: {timestamp}, ошибка: {str(e)}")
            continue

    return filtered


@app.post("/generate_table/{chat_id}")
async def generate_table(
        chat_id: str,
        request: TableRequest
):
    """Generates a table directly from message data."""
    # Get data
    messages = await fetch_processed_messages(chat_id)
    
    # Filter by time
    filtered = filter_messages_by_time(
        messages,
        request.time.start,
        request.time.end,
        request.time.format
    )

    if not filtered:
        df = pd.DataFrame(columns=request.columns)
        return generate_table_response(df, TableFormat(request.format), f"{chat_id}_empty")

    # Create dataframe directly from data
    df = create_dataframe_from_data(filtered, request.columns)

    # Format and send response
    return generate_table_response(df, TableFormat(request.format), f"{chat_id}_data")


@app.post("/generate_chart/{chat_id}")
async def generate_chart(
        chat_id: str,
        request: ChartRequest
) -> ChartResponse:
    """Generates chart data directly from message data."""
    # Get data
    messages = await fetch_processed_messages(chat_id)

    # Filter by time
    filtered = filter_messages_by_time(
        messages,
        request.time.start,
        request.time.end,
        request.time.format
    )

    # Generate chart data directly from data
    return generate_chart_data_from_data(
        filtered,
        request.chart_definition
    )

# --- Main Execution ---
def main():
    import uvicorn
    logger.info(f"Starting Message Processing Service on port {API_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)

if __name__ == "__main__":
    main()