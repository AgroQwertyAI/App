from typing import Literal
import os
import requests
from dotenv import load_dotenv
from src.config import logger
from src.auxiliary.logging import log_info

# Load environment variables
load_dotenv()

def send_report(
    file: str, 
    messenger: Literal['telegram', 'whatsapp'], 
    number: str
):
    """
    Send a report file to a user via the specified messenger.
    
    Args:
        file: Base64 encoded file content with data URI
        messenger: The messenger service to use ('telegram' or 'whatsapp')
        number: The user's contact number or chat ID
    """
    log_info(f"Starting to send report via {messenger} to {number}", 'info')
    
    # Get WhatsApp service address from environment variables
    whatsapp_service_url = os.getenv('WHATSAPP_SERVICE_URL', 'http://whatsapp-service:52101')
    
    # Validate file format
    if not isinstance(file, str) or not file.startswith('data:'):
        logger.error("File is not in correct data URI format")
        return
    
    if messenger == 'whatsapp':
        # Check file size
        file_size = len(file)
        logger.info(f"File size: {file_size} characters")
        
        # File too large? WhatsApp generally limits files to around 16MB
        if file_size > 22000000:  # ~16MB in base64 is roughly 22M chars
            logger.error(f"File too large ({file_size} chars) - may exceed WhatsApp limits")
        
        # Set endpoint for sending files
        endpoint = f"{whatsapp_service_url}/send_file"
        
        # Prepare request data
        data = {
            "user": number,
            "file": file,
            "filename": "report.xlsx",
            "caption": "Отчёт"
        }
        
        try:
            # Add timeout to prevent hanging requests
            logger.info(f"Sending request to {endpoint}")
            response = requests.post(endpoint, json=data, timeout=30)
            
            # Check if request was successful
            if response.status_code == 200:
                logger.info(f"Report successfully sent to WhatsApp user {number}")
            else:
                logger.error(f"Failed to send report: {response.status_code} - {response.text}")
                try:
                    error_detail = response.json()
                    logger.error(f"Error details: {error_detail}")
                except:
                    pass
                
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to WhatsApp service at {whatsapp_service_url} - check if service is running and accessible")
        except requests.exceptions.Timeout:
            logger.error("Request timed out - file may be too large or service is unresponsive")
        except Exception as e:
            logger.error(f"Error sending report to WhatsApp: {str(e)}")

    elif messenger == 'telegram':
        telegram_bot_service_url = os.getenv('TELEGRAM_BOT_SERVICE_URL', 'http://telegram-bot-service:7999')
        endpoint = f"{telegram_bot_service_url}/send_file"
        data = {
            "chat_id": number,
            "file": file,
            "filename": "report.xlsx",
            "caption": "Отчёт",
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        try:
            response = requests.post(endpoint, json=data, timeout=30)
            if response.status_code == 200:
                logger.info(f"Report successfully sent to Telegram user {number}")
            else:
                logger.error(f"Failed to send report: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error sending report to Telegram: {str(e)}")
            raise
