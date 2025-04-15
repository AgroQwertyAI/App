from datetime import datetime
import os
import json
import pandas as pd
import base64
from src.session import get_session
from datetime import datetime
from src.newsletter import send_report
import shutil
from src.auxiliary.logging import log_info
from src.generating_reports.helper import (
    get_pending_messages, 
    aggregate_messages, 
    save_report_to_db,
    get_image_binary_from_base64,
    save_message_report_to_db,
    delete_pending_messages,
    convert_dataframe_to_bytes_xlsx,
    get_aggregated_json_from_messages,
    group_messages_by_sender
)

def save_filesystem_report(setting: dict) -> str:
    # Extract setting ID from the setting dictionary
    setting_id = setting["setting_id"]

    with get_session() as conn:
        # 1. Fetch all pending messages associated with the setting
        pending_messages = get_pending_messages(setting_id, conn)
        
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
            
            file_content = convert_dataframe_to_bytes_xlsx(df)
            file = f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{base64.b64encode(file_content).decode('utf-8')}"
        
        # 4. Create a new Report record
        report_id = save_report_to_db(setting_id, file, conn)
        
        messages_by_sender = group_messages_by_sender(pending_messages)
        
        # Process each sender's messages as a group
        for sender_id, sender_messages in messages_by_sender.items():
            user_dir = f"{messages_dir}/{sender_id}"

            for i, message in enumerate(sender_messages):
                # 4.1 Save raw texts associated with a message
                os.makedirs(f"{user_dir}/{i}", exist_ok=True)
                with open(f"{user_dir}/{i}/text.txt", "w") as f:
                    f.write(message["original_message_text"])

                # 4.2 Save formatted text associated with a message
                with open(f"{user_dir}/{i}/formatted_text.json", "w") as f:
                    f.write(message["formatted_message_text"])

                # 4.3 save images
                images = json.loads(message["images"]) if message["images"] else {"images": []}
                os.makedirs(f"{user_dir}/{i}/images", exist_ok=True)
                for j, image in enumerate(images["images"]):
                    # Save the base64 encoded image with index to keep them separate
                    try:
                        image_binary, image_extension = get_image_binary_from_base64(image)
                        
                        # Write binary data to file with index suffix
                        with open(f"{user_dir}/{i}/images/image_{j}.{image_extension}", "wb") as f:
                            f.write(image_binary)
                    except Exception:
                        log_info(f"Error saving image", 'error')

                # save message to db
                save_message_report_to_db(message, report_id, conn)

        # 4.4 Aggregate formatted_message_text JSON objects
        aggregated_json = get_aggregated_json_from_messages(pending_messages)
        
        # Save aggregated formatted text
        with open(f"{report_dir}/formatted_text.json", "w") as f:
            f.write(json.dumps(aggregated_json))

        # 6. Delete previous messages_pending for this setting
        delete_pending_messages(setting_id, conn)
        
        # Commit is handled by the context manager

    return file

def move_local_report_to_deleted(setting_id: int):
    source_dir = f"/reports/active/{setting_id}"
    target_dir = f"/reports/deleted/{setting_id}"
    
    # Check if source directory exists
    if os.path.exists(source_dir):
        # Create target directory if it doesn't exist
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        
        # Move the directory
        shutil.move(source_dir, target_dir)
        log_info(f"Moved report folder from {source_dir} to {target_dir}", 'info')
    else:
        log_info(f"Report folder not found at {source_dir}, skipping move", 'info')