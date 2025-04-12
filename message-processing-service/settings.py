import os
import json
import aiohttp
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import requests
import logging
from datetime import datetime


# Load environment variables
load_dotenv()

# Service URLs
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:3000")

def get_template_by_id(template_id: str) -> Optional[Dict[Any, Any]]:
    """
    Retrieves a chat template by its ID.
    
    Args:
        template_id: The MongoDB ObjectId of the template as a string
        base_url: The base URL of the API (defaults to localhost:3000)
        
    Returns:
        The template data as a dictionary if found, None otherwise
        
    Raises:
        requests.RequestException: If there's a network error
        ValueError: If the template_id is invalid
        Exception: For other unexpected errors
    """
    if not template_id:
        raise ValueError("Template ID cannot be empty")
        
    try:
        # Make GET request to the templates endpoint with ID parameter
        response = requests.get(f"{DATA_SERVICE_URL}/api/templates", params={"id": template_id})
        
        # Check if request was successful
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"Template with ID {template_id} not found")
            return None
        else:
            # Handle other status codes
            error_data = response.json()
            print(f"Error retrieving template: {error_data.get('error', 'Unknown error')}")
            return None
            
    except requests.RequestException as e:
        print(f"Network error occurred: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise

async def get_template_id(chat_id: str):
    """
    Checks if a chat should be monitored by querying the Data Service.
    Returns True if the chat is active and should be monitored, False otherwise.
    """
    url = f"{DATA_SERVICE_URL}/api/chats/{chat_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    chat_data = await response.json()
                    id = chat_data.get('template_id', 0)
                    return id
    except aiohttp.ClientError as e:
        return True
    except Exception as e:
        return True