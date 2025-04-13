from yadisk import YaDisk
from datetime import datetime
import json
import pandas as pd
import base64
import io
from src.session import get_session
from src.config import logger
from src.newsletter import send_report
from collections import defaultdict
from pathlib import Path
from src.generating_reports.helper import (
    get_pending_messages, 
    aggregate_messages, 
    save_report_to_db,
    get_image_binary_from_base64,
    save_message_report_to_db,
    delete_pending_messages
)

OAUTH_CONFIG_DIR = Path("/config")
CONFIG_FILE_YANDEX_DISK = OAUTH_CONFIG_DIR / "yandex_oauth.json"


def get_yandex_disk_config():
    """Get the full Yandex Disk configuration data."""
    with open(CONFIG_FILE_YANDEX_DISK, "r") as f:
        data = json.load(f)
    return data


def save_yandex_disk_report_and_send_messages(setting: dict) -> bool:
    # Extract setting ID from the setting dictionary
    setting_id = setting["setting_id"]
    logger.info(f"Saving report and sending messages for setting {setting_id}")

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
        print(get_yandex_disk_config())
        current_token = get_yandex_disk_config()["token"]
        if not current_token:
            logger.error("No Yandex OAuth token found")
            raise Exception("No Yandex OAuth token found")
        
        # Initialize YaDisk client
        y = YaDisk(token=current_token)
        # Create report directories on Yandex Disk
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

        shared_folder_name = get_yandex_disk_config()["shared_folder_name"]
        report_dir = f"/{shared_folder_name}/reports/active/{setting_id}/{timestamp}"
        messages_dir = f"{report_dir}/messages"
        
        # Create directories on Yandex Disk if do not exist
        if not y.exists(report_dir):
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
        
        # Group messages by sender_id
        messages_by_sender = defaultdict(list)
        for message in pending_messages:
            sender_id = message["sender_id"]
            messages_by_sender[sender_id].append(message)
        
        # Process each sender's messages as a group
        for sender_id, sender_messages in messages_by_sender.items():
            user_dir = f"{messages_dir}/{sender_id}"
            
            # Create user directory on Yandex Disk
            y.mkdir(user_dir)
            
            # 1. Aggregate original_message_text with [SEP] separators
            aggregated_text = ""
            for i, message in enumerate(sender_messages):
                if i > 0:
                    aggregated_text += "\n[SEP]\n"
                aggregated_text += message["original_message_text"]
            
            # Save aggregated raw text
            raw_text_buffer = io.BytesIO(aggregated_text.encode('utf-8'))
            y.upload(raw_text_buffer, f"{user_dir}/raw_text.txt")
            
            # 2. Aggregate formatted_message_text JSON objects
            aggregated_json = {}
            for message in sender_messages:
                message_json = json.loads(message["formatted_message_text"])
                for field, value in message_json.items():
                    if field not in aggregated_json:
                        aggregated_json[field] = [value]
                    else:
                        aggregated_json[field].append(value)
            
            # Save aggregated formatted text
            formatted_text_buffer = io.BytesIO(json.dumps(aggregated_json).encode('utf-8'))
            y.upload(formatted_text_buffer, f"{user_dir}/formatted_text.json")
            
            # Handle images from all messages
            i = 0
            for message in sender_messages:
                images = json.loads(message["images"]) if message["images"] else {"images": []}
                for image in images["images"]:
                    # Save the base64 encoded image with index to keep them separate
                    try:
                        image_binary, image_extension = get_image_binary_from_base64(image)
                        
                        # Upload image directly from memory with index suffix
                        image_buffer = io.BytesIO(image_binary)
                        y.upload(image_buffer, f"{user_dir}/image_{i}.{image_extension}")
                        i += 1
                    except Exception as e:
                        logger.error(f"Error saving image: {e}")
            
            # Create MessageReport records for each original message
            for message in sender_messages:
                save_message_report_to_db(message, report_id, conn)
        
        # 6. Delete previous messages_pending for this setting
        delete_pending_messages(setting_id, conn)
        
    return True
    
def move_yandex_disk_report_to_deleted(setting_id: int):
    try:
        # Get the current OAuth token
        current_token = get_yandex_disk_config()["token"]
        
        # Initialize YaDisk client
        y = YaDisk(token=current_token)

        shared_folder_name = get_yandex_disk_config()["shared_folder_name"]
        # Define source and target paths
        source_path = f"/{shared_folder_name}/reports/active/{setting_id}"
        target_path = f"/{shared_folder_name}/reports/deleted/{setting_id}"
        
        # Check if source path exists
        if y.exists(source_path):
            # Make sure target parent directory exists
            if not y.exists(f"{shared_folder_name}/reports/deleted"):
                y.mkdir(f"{shared_folder_name}/reports/deleted")
                logger.info(f"Created {shared_folder_name}/reports/deleted directory")
                
            # Move the directory
            y.move(source_path, target_path, overwrite=True)
            logger.info(f"Moved report folder from {source_path} to {target_path}")
        else:
            logger.info(f"Report folder not found at {source_path}, skipping move")
    
    except Exception as e:
        logger.error(f"Error moving report for setting ID {setting_id}: {str(e)}")