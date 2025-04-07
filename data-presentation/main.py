import os
import logging
from typing import List, Dict, Any, Optional

import uvicorn
import aiohttp
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from dotenv import load_dotenv

from generators import (
    create_dataframe,
    generate_table_response,
    generate_chart_data,
    TableFormat
)

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


async def fetch_processed_messages(chat_id: str) -> List[Dict[str, Any]]:
    """Gets processed messages for the specified chat_id."""
    url = f"{DATA_SERVICE_URL}/api/chats/messages/{chat_id}"
    data = await fetch_data_service(url)

    if not isinstance(data, list):
        raise HTTPException(status_code=502,
                            detail="Invalid data format from data service (expected list)")

    return data


def filter_messages_by_type(messages: List[Dict[str, Any]], incident_type: Optional[str]) -> List[Dict[str, Any]]:
    """Filters messages by incident type."""
    if not incident_type or incident_type.lower() == 'any':
        return messages

    return [msg for msg in messages
            if isinstance(msg, dict) and
            msg.get("type") == incident_type]


def create_empty_response(format: TableFormat, filename_base: str) -> Response:
    """Creates an empty response in the required format."""
    df = pd.DataFrame()
    return generate_table_response(df, format, filename_base)


@app.get("/generate_table")
async def get_table(
        chat_id: str = Query(description="Chat ID to get messages"),
        format: TableFormat = Query(description="Desired output format"),
        type: str = Query('any', description="Filter by incident type")
):
    """Generates data table in the requested format."""
    # Get data
    messages = await fetch_processed_messages(chat_id)

    # Filter data
    filter_type = None if type.lower() == 'any' else type
    filtered = filter_messages_by_type(messages, filter_type)

    # Create empty response if no data
    if not filtered:
        filename_type = type.replace(" ", "_") if filter_type else 'all'
        filename_base = f"{chat_id}_{filename_type}_messages"
        return create_empty_response(format, filename_base)

    # Create DataFrame and response
    df = create_dataframe(filtered)
    filename_type = type.replace(" ", "_") if filter_type else 'all'
    filename_base = f"{chat_id}_{filename_type}_messages"

    return generate_table_response(df, format, filename_base)


@app.get("/generate_chart")
async def get_chart(
        chat_id: str = Query(description="Chat ID to get messages"),
        chart_type: str = Query(description="Chart type")
):
    """Generates data for charts of the specified type."""
    messages = await fetch_processed_messages(chat_id)
    return generate_chart_data(messages, chart_type)


if __name__ == "__main__":
    logger.info(f"Starting data presentation service on port {API_PORT}")
    logger.info(f"Connecting to data service at {DATA_SERVICE_URL}")
    uvicorn.run(app, host="127.0.0.1", port=API_PORT)
