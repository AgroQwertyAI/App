from yadisk import YaDisk
from datetime import datetime
import json
import pandas as pd
import base64
import io
from src.session import get_session
import logging
from src.newsletter import send_report
from pathlib import Path

from src.generating_reports.helper import (
    get_pending_messages, 
    aggregate_messages, 
    save_report_to_db,
    get_image_binary_from_base64,
    save_message_report_to_db,
    delete_pending_messages
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the path for storing the token
OAUTH_CONFIG_DIR = Path("config")
OAUTH_CONFIG_FILE = OAUTH_CONFIG_DIR / "yandex_oauth.json"


def get_oauth_token():
    """Get the OAuth token from the configuration file."""
    if OAUTH_CONFIG_FILE.exists():
        with open(OAUTH_CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("token")
    else:
        return None


def save_yandex_disk_report_and_send_messages(setting: dict) -> bool:
    # Extract setting ID from the setting dictionary
    setting_id = setting["setting_id"]
    
    with get_session() as conn:
        # 1. Fetch all pending messages associated with the setting
        pending_messages = get_pending_messages(setting_id, conn)
        
        if not pending_messages:
            return False
        
        # 2. Aggregate formatted text into one JSON
        aggregated_data = aggregate_messages(pending_messages)
        
        # 3. Create a table based on setting schema (currently only xlsx supported)
        report_format = setting["format_report"]
        
        # Get the current OAuth token
        current_token = get_oauth_token()
        if not current_token:
            logger.error("No Yandex OAuth token found")
            raise Exception("No Yandex OAuth token found")
        
        # Initialize YaDisk client
        y = YaDisk(token=current_token)
        
        # Create report directories on Yandex Disk
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        report_dir = f"/reports/active/{setting_id}/{timestamp}"
        messages_dir = f"{report_dir}/messages"
        
        # Create directories on Yandex Disk
        y.makedirs(report_dir)
        y.makedirs(messages_dir)
        
        # Generate xlsx file
        df = pd.DataFrame(aggregated_data)
        
        # Create base64 encoded file content
        file = ""
        if report_format == "xlsx":
            # Create Excel file in memory
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            buffer.seek(0)
            file_content = buffer.read()
            
            # Upload to Yandex Disk directly from memory
            memory_file = io.BytesIO(file_content)
            y.upload(memory_file, f"{report_dir}/report.{report_format}")
            
            # Create base64 encoded version for database
            file = f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{base64.b64encode(file_content).decode('utf-8')}"
        
        # 4. Create a new Report record
        report_id = save_report_to_db(setting_id, file, conn)

        for message in json.loads(setting['send_to']) if isinstance(setting['send_to'], str) else setting['send_to']:
            send_report(file, message['messenger'], message['phone_number'])
        
        # Create MessageReport objects
        for message in pending_messages:
            user_id = message["sender_id"]
            user_dir = f"{messages_dir}/{user_id}"
            
            # Create user directory on Yandex Disk
            y.mkdir(user_dir)
            
            # 5. Save message files in Yandex Disk
            # Save raw text directly from memory
            raw_text = message["original_message_text"]
            raw_text_buffer = io.BytesIO(raw_text.encode('utf-8'))
            y.upload(raw_text_buffer, f"{user_dir}/raw_text.txt")
            
            # Save formatted text directly from memory
            formatted_text = message["formatted_message_text"]
            formatted_text_buffer = io.BytesIO(formatted_text.encode('utf-8'))
            y.upload(formatted_text_buffer, f"{user_dir}/formatted_text.json")
            
            # Handle extra data (like images) if they exist
            extra_data = json.loads(message["extra"] if message["extra"] else "{}")
            if extra_data and "image" in extra_data:
                image_data = extra_data["image"]
                
                # Save the base64 encoded image
                if "data" in image_data:
                    try:
                        image_binary, image_extension = get_image_binary_from_base64(image_data["data"])
                        
                        # Upload image directly from memory
                        image_buffer = io.BytesIO(image_binary)
                        y.upload(image_buffer, f"{user_dir}/image.{image_extension}")
                    except Exception as e:
                        logger.error(f"Error saving image: {e}")
            
            # Create MessageReport record
            save_message_report_to_db(message, report_id, conn)
        
        # 6. Delete previous messages_pending for this setting
        delete_pending_messages(setting_id, conn)
        
    return True
    
def move_yandex_disk_report_to_deleted(setting_id: int):
    try:
        # Get the current OAuth token
        current_token = get_oauth_token()
        
        # Initialize YaDisk client
        y = YaDisk(token=current_token)
        
        # Define source and target paths
        source_path = f"/reports/active/{setting_id}"
        target_path = f"/reports/deleted/{setting_id}"
        
        # Check if source path exists
        if y.exists(source_path):
            # Make sure target parent directory exists
            if not y.exists("/reports/deleted"):
                y.mkdir("/reports/deleted")
                logger.info("Created /reports/deleted directory")
                
            # Move the directory
            y.move(source_path, target_path, overwrite=True)
            logger.info(f"Moved report folder from {source_path} to {target_path}")
        else:
            logger.info(f"Report folder not found at {source_path}, skipping move")
    
    except Exception as e:
        logger.error(f"Error moving report for setting ID {setting_id}: {str(e)}")