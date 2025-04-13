from datetime import datetime
import os
import json
import pandas as pd
import base64
import io
from src.session import get_session
import logging
from datetime import datetime
from src.newsletter import send_report
import shutil
from collections import defaultdict
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

def save_filesystem_report_and_send_messages(setting: dict) -> bool:
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
        
        # Create report directories
        report_dir = f"/reports/active/{setting_id}/{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
        os.makedirs(report_dir, exist_ok=True)
        messages_dir = f"{report_dir}/messages"
        os.makedirs(messages_dir, exist_ok=True)
        
        # Generate xlsx file
        df = pd.DataFrame(aggregated_data)
        report_path = f"{report_dir}/report.{report_format}"
        
        # Create base64 encoded file content
        file = ""
        if report_format == "xlsx":
            # First save to disk for user access
            df.to_excel(report_path, index=False)
            
            # Then create base64 encoded version for database
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            buffer.seek(0)
            file_content = buffer.read()
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
            os.makedirs(user_dir, exist_ok=True)
            
            # 1. Aggregate original_message_text with [SEP] separators
            aggregated_text = ""
            for i, message in enumerate(sender_messages):
                if i > 0:
                    aggregated_text += "\n[SEP]\n"
                aggregated_text += message["original_message_text"]
            
            # Save aggregated raw text
            with open(f"{user_dir}/raw_text.txt", "w") as f:
                f.write(aggregated_text)
            
            # 2. Aggregate formatted_message_text JSON objects
            aggregated_json = {}
            for message in sender_messages:
                message_json = json.loads(message["formatted_message_text"])
                for field, values in message_json.items():
                    if field not in aggregated_json:
                        aggregated_json[field] = []
                    aggregated_json[field].extend(values)
            
            # Save aggregated formatted text
            with open(f"{user_dir}/formatted_text.json", "w") as f:
                f.write(json.dumps(aggregated_json))

            # Handle images from all messages
            for message in sender_messages:
                images = json.loads(message["images"]) if message["images"] else {"images": []}
                for i, image in enumerate(images["images"]):
                    # Save the base64 encoded image with index to keep them separate
                    try:
                        image_binary, image_extension = get_image_binary_from_base64(image)
                        
                        # Write binary data to file with index suffix
                        with open(f"{user_dir}/image_{i}.{image_extension}", "wb") as f:
                            f.write(image_binary)
                    except Exception as e:
                        logger.error(f"Error saving image: {e}")

            # Create MessageReport records for each original message
            for message in sender_messages:
                save_message_report_to_db(message, report_id, conn)

        # 6. Delete previous messages_pending for this setting
        delete_pending_messages(setting_id, conn)
        
        # Commit is handled by the context manager

    return None

def move_local_report_to_deleted(setting_id: int):
    source_dir = f"/reports/active/{setting_id}"
    target_dir = f"/reports/deleted/{setting_id}"
    
    # Check if source directory exists
    if os.path.exists(source_dir):
        # Create target directory if it doesn't exist
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        
        # Move the directory
        shutil.move(source_dir, target_dir)
        logger.info(f"Moved report folder from {source_dir} to {target_dir}")
    else:
        logger.info(f"Report folder not found at {source_dir}, skipping move")