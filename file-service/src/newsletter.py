from typing import Literal
import os
import requests
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

def send_report(
    file: str, 
    messenger: Literal['telegram', 'whatsapp'], 
    number: str
):
    """
    Send a report file to a user via the specified messenger.
    
    Args:
        file: Base64 encoded file content
        messenger: The messenger service to use ('telegram' or 'whatsapp')
        number: The user's contact number or chat ID
    """
    logger.info(str(messenger) + str(number) + str(os.getenv('WHATSAPP_SERVICE_URL')))


    # Only proceed if messenger is whatsapp
    if messenger != "whatsapp":
        return
    
    # Load environment variables
    load_dotenv()
    
    # Get WhatsApp service address from environment variables
    whatsapp_service_url = os.getenv('WHATSAPP_SERVICE_URL')
    if not whatsapp_service_url:
        raise ValueError("WHATSAPP_SERVICE_URL environment variable not set")
    
    # Set endpoint for sending files
    endpoint = f"{whatsapp_service_url}/send_file"
    
    # Prepare request data
    data = {
        "user": number,
        "file": file,
        "filename": "report.pdf",
        "caption": "Отчёт"
    }
    
    try:
        # Send request to WhatsApp service
        response = requests.post(endpoint, json=data)
        
        # Check if request was successful
        if response.status_code == 200:
            print(f"Report successfully sent to WhatsApp user {number}")
        else:
            print(f"Failed to send report: {response.json().get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Error sending report to WhatsApp: {str(e)}")