import yadisk
import json
from datetime import datetime
import pandas as pd
import base64
import io
from src.auxiliary.logging import log_info
from src.session import get_session
from pathlib import Path
import asyncio
from src.generating_reports.helper import (
    get_pending_messages, 
    aggregate_messages, 
    save_report_to_db,
    get_image_binary_from_base64,
    save_message_report_to_db,
    delete_pending_messages,
    convert_dataframe_to_bytes_xlsx,
    group_messages_by_sender,
    get_aggregated_json_from_messages
)

OAUTH_CONFIG_DIR = Path("/config")
CONFIG_FILE_YANDEX_DISK = OAUTH_CONFIG_DIR / "yandex_oauth.json"


def get_yandex_disk_config():
    """Get the full Yandex Disk configuration data."""
    try:
        with open(CONFIG_FILE_YANDEX_DISK, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        log_info(f"Error getting Yandex Disk config: {e}", 'error')
        return None
    
def get_yandex_disk_folder_path() -> str:
    config = get_yandex_disk_config()

    shared_folder_link_or_path = config["shared_folder_name"]
    y = yadisk.YaDisk(token=config["token"])

    try:
        public_resource = y.get_public_meta(shared_folder_link_or_path)
        return public_resource.name
    except Exception:
        pass

    return shared_folder_link_or_path

async def save_yandex_disk_report(setting: dict) -> str:
    # Extract setting ID from the setting dictionary
    setting_id = setting["setting_id"]
    log_info(f"Saving report and sending messages for setting {setting_id}", 'info')

    with get_session() as conn:
        # 1. Fetch all pending messages associated with the setting
        pending_messages = get_pending_messages(setting_id, conn)
    
    # 2. Aggregate formatted text into one JSON
    aggregated_data = aggregate_messages(pending_messages)
    
    # 3. Create a table based on setting schema (currently only xlsx supported)
    report_format = setting["format_report"]
    
    # Get the current OAuth token
    current_token = get_yandex_disk_config()["token"]
    if not current_token:
        log_info("No Yandex OAuth token found", 'error')
        raise Exception("No Yandex OAuth token found")
    
    # Initialize YaDisk client
    y = yadisk.YaDisk(token=current_token)
    # Create report directories on Yandex Disk
    timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    shared_folder_path = get_yandex_disk_folder_path()

    report_dir = f"/{shared_folder_path}/reports/active/{setting_id}/{timestamp}"
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
        file_content = convert_dataframe_to_bytes_xlsx(df)
        
        # Upload to Yandex Disk directly from memory
        memory_file = io.BytesIO(file_content)
        y.upload(memory_file, f"{report_dir}/report.{report_format}")
        
        # Create base64 encoded version for database
        file = f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{base64.b64encode(file_content).decode('utf-8')}"
    
    with get_session() as conn:
        # 4. Create a new Report record
        report_id = save_report_to_db(setting_id, file, conn)
    
    messages_by_sender = group_messages_by_sender(pending_messages)

    requests = []
    
    y = yadisk.AsyncClient(token=current_token)
    # Process each sender's messages as a group
    for sender_id, sender_messages in messages_by_sender.items():
        user_dir = f"{messages_dir}/{sender_id}"
    
        # Create user directory on Yandex Disk
        requests.append(y.mkdir(user_dir))

    await asyncio.gather(*requests)

    requests = []
    
    for sender_id, sender_messages in messages_by_sender.items():
        user_dir = f"{messages_dir}/{sender_id}"
        
        # 4.1 Save each message separately
        for i, message in enumerate(sender_messages):
            # Create a folder for this message
            message_folder = f"{user_dir}/{i}"
            requests.append(y.mkdir(message_folder))

    await asyncio.gather(*requests)

    requests = []

    for sender_id, sender_messages in messages_by_sender.items():
        user_dir = f"{messages_dir}/{sender_id}"

        for i, message in enumerate(sender_messages):
            message_folder = f"{user_dir}/{i}"
            images_folder = f"{message_folder}/images"
            requests.append(y.mkdir(images_folder))
            
    await asyncio.gather(*requests)

    requests = []

    for sender_id, sender_messages in messages_by_sender.items():
        user_dir = f"{messages_dir}/{sender_id}"

        for i, message in enumerate(sender_messages):
            message_folder = f"{user_dir}/{i}"
            images_folder = f"{message_folder}/images"

            # Save individual message text
            text_buffer = io.BytesIO(message["original_message_text"].encode('utf-8'))
            requests.append(y.upload(text_buffer, f"{message_folder}/text.txt"))
            
            # 4.2 Save formatted text associated with a message
            formatted_text_buffer = io.BytesIO(message["formatted_message_text"].encode('utf-8'))
            requests.append(y.upload(formatted_text_buffer, f"{message_folder}/formatted_text.json"))
            
            # 4.3 save images
            images = json.loads(message["images"]) if message["images"] else {"images": []}
            
            # Save each image for this message
            for j, image in enumerate(images["images"]):
                # Save the base64 encoded image with index to keep them separate
                try:
                    image_binary, image_extension = get_image_binary_from_base64(image)
                    
                    # Upload image directly from memory with index suffix
                    image_buffer = io.BytesIO(image_binary)
                    requests.append(y.upload(image_buffer, f"{images_folder}/image_{j}.{image_extension}"))
                except Exception as e:
                    log_info(f"Error saving image", 'error')

            with get_session() as conn:
                # save message to db
                save_message_report_to_db(message, report_id, conn)
            
    await asyncio.gather(*requests)

    # 4.4 Aggregate formatted_message_text JSON objects
    aggregated_json = get_aggregated_json_from_messages(pending_messages)
    
    # Save aggregated formatted text
    aggregated_json_buffer = io.BytesIO(json.dumps(aggregated_json).encode('utf-8'))
    await y.upload(aggregated_json_buffer, f"{report_dir}/formatted_text.json")

    with get_session() as conn:
        # 6. Delete previous messages_pending for this setting
        delete_pending_messages(setting_id, conn)
        
    return file
    
def move_yandex_disk_report_to_deleted(setting_id: int):
    try:
        # Get the current OAuth token
        current_token = get_yandex_disk_config()["token"]
        
        # Initialize YaDisk client
        y = yadisk.YaDisk(token=current_token)

        shared_folder_name = get_yandex_disk_config()["shared_folder_name"]
        # Define source and target paths
        source_path = f"/{shared_folder_name}/reports/active/{setting_id}"
        target_path = f"/{shared_folder_name}/reports/deleted/{setting_id}"
        
        # Check if source path exists
        if y.exists(source_path):
            # Make sure target parent directory exists
            if not y.exists(f"{shared_folder_name}/reports/deleted"):
                y.mkdir(f"{shared_folder_name}/reports/deleted")
                log_info(f"Created {shared_folder_name}/reports/deleted directory", 'info')
                
            # Move the directory
            y.move(source_path, target_path, overwrite=True)
            log_info(f"Moved report folder from {source_path} to {target_path}", 'info')
        else:
            log_info(f"Report folder not found at {source_path}, skipping move", 'info')
    
    except Exception as e:
        log_info(f"Error moving report for setting ID {setting_id}: {e}", 'error')