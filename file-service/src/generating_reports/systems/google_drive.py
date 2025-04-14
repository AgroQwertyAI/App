from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaInMemoryUpload
from google.oauth2 import service_account
from datetime import datetime
import json
import pandas as pd
import base64
import io
from src.session import get_session
from src.newsletter import send_report
from pathlib import Path
import tempfile
import os
from src.generating_reports.helper import (
    get_pending_messages, 
    aggregate_messages, 
    save_report_to_db,
    get_image_binary_from_base64,
    save_message_report_to_db,
    delete_pending_messages
)
from collections import defaultdict
from src.config import logger

OAUTH_CONFIG_DIR = Path("/config")
CONFIG_FILE_GOOGLE_DRIVE = OAUTH_CONFIG_DIR / "google_drive_credentials.json"

def get_google_drive_config():
    """Get the Google Drive credentials from the configuration file."""
    try:
        with open(CONFIG_FILE_GOOGLE_DRIVE, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        logger.error(f"Error getting Google Drive config: {e}")
        return None

def get_drive_service():
    """Create and return a Google Drive service instance"""
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    # Get credentials from config file
    config = get_google_drive_config()
    
    if not config:
        raise Exception("No Google Drive credentials found")
    
    # Write service account JSON to temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
        json.dump(config["service_account_json"], temp_file)
        temp_filename = temp_file.name

    try:
        credentials = service_account.Credentials.from_service_account_file(
            temp_filename, scopes=SCOPES
        )
        
        service = build('drive', 'v3', credentials=credentials)
        return service
    finally:
        # Clean up temporary file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

def create_folder(service, name, parent_id=None):
    """Create a folder in Google Drive and return its ID"""
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def find_or_create_path(service, path):
    """Find or create a path in Google Drive and return the last folder ID"""
    parts = path.strip('/').split('/')
    parent_id = None
    
    for part in parts:
        # Search for the folder in the current parent
        query = f"name='{part}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        items = results.get('files', [])
        
        if items:
            parent_id = items[0]['id']
        else:
            # Folder doesn't exist, create it
            parent_id = create_folder(service, part, parent_id)
    
    return parent_id

def upload_file(service, file_content, filename, parent_id, mime_type):
    """Upload a file to Google Drive and return its ID"""
    file_metadata = {
        'name': filename,
        'parents': [parent_id]
    }
    
    if isinstance(file_content, io.BytesIO):
        media = MediaIoBaseUpload(file_content, mimetype=mime_type, resumable=True)
    elif isinstance(file_content, bytes):
        media = MediaInMemoryUpload(file_content, mimetype=mime_type, resumable=True)
    else:
        # Convert string content to bytes if needed
        content_bytes = file_content if isinstance(file_content, bytes) else file_content.encode('utf-8')
        media = MediaInMemoryUpload(content_bytes, mimetype=mime_type, resumable=True)
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    
    return file.get('id')

def find_shared_folder(service):
    """Find a folder that has been shared with the service account"""
    # Get folder name from config, or use default
    config = get_google_drive_config()
    folder_name = config["shared_folder_name"]
    
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if not items:
        logger.error(f"Shared folder '{folder_name}' not found. Please make sure it's shared with the service account.")
        return None
        
    return items[0]['id']

def save_google_drive_report_and_send_messages(setting: dict) -> bool:
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
        
        # Initialize Google Drive service
        service = get_drive_service()
        
        # Find the shared agriculture folder
        base_folder_id = find_shared_folder(service)
        if not base_folder_id:
            logger.error("Cannot proceed without access to the shared folder")
            return False
        
        # Create report directories on Google Drive with the shared folder as base
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        folder_structure = f"reports/active/{setting_id}/{timestamp}"
        
        # Find or create the folder structure under the agriculture folder
        current_parent_id = base_folder_id
        for folder_name in folder_structure.split('/'):
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{current_parent_id}' in parents and trashed=false"
            results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            items = results.get('files', [])
            
            if items:
                current_parent_id = items[0]['id']
            else:
                current_parent_id = create_folder(service, folder_name, current_parent_id)
        
        report_dir_id = current_parent_id
        messages_dir_id = create_folder(service, "messages", report_dir_id)
        
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
            
            # Upload to Google Drive directly from memory
            memory_file = io.BytesIO(file_content)
            upload_file(
                service, 
                memory_file, 
                f"report.{report_format}", 
                report_dir_id,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
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
            # Create user directory on Google Drive
            user_dir_name = str(sender_id)
            user_dir_id = create_folder(service, user_dir_name, messages_dir_id)
            
            # 1. Aggregate original_message_text with [SEP] separators
            aggregated_text = ""
            for i, message in enumerate(sender_messages):
                if i > 0:
                    aggregated_text += "\n[SEP]\n"
                aggregated_text += message["original_message_text"]
            
            # Save aggregated raw text
            upload_file(
                service,
                aggregated_text.encode('utf-8'),
                "raw_text.txt",
                user_dir_id,
                'text/plain'
            )
            
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
            upload_file(
                service,
                json.dumps(aggregated_json).encode('utf-8'),
                "formatted_text.json",
                user_dir_id,
                'application/json'
            )
            
            # Handle images from all messages
            i = 0
            for message in sender_messages:
                images = json.loads(message["images"]) if message["images"] else {"images": []}
                for image in images["images"]:
                    # Save the base64 encoded image with index to keep them separate
                    try:
                        image_binary, image_extension = get_image_binary_from_base64(image)
                        
                        # Upload image directly from memory with index suffix
                        mime_type = f"image/{image_extension}" if image_extension != "jpg" else "image/jpeg"
                        upload_file(
                            service,
                            image_binary,
                            f"image_{i}.{image_extension}",
                            user_dir_id,
                            mime_type
                        )
                        i += 1
                    except Exception as e:
                        logger.error(f"Error saving image: {e}")
            
            # Create MessageReport records for each original message
            for message in sender_messages:
                save_message_report_to_db(message, report_id, conn)
        
        # 6. Delete previous messages_pending for this setting
        delete_pending_messages(setting_id, conn)
        
    return True

def move_google_drive_report_to_deleted(setting_id: int):
    try:
        # Initialize Google Drive service
        service = get_drive_service()
        
        # Find the shared agriculture folder
        base_folder_id = find_shared_folder(service)
        if not base_folder_id:
            logger.error("Cannot proceed without access to the shared folder")
            return
        
        # Find reports folder in the shared folder
        reports_query = f"name='reports' and mimeType='application/vnd.google-apps.folder' and '{base_folder_id}' in parents and trashed=false"
        reports_results = service.files().list(q=reports_query, spaces='drive', fields='files(id)').execute()
        reports_items = reports_results.get('files', [])
        
        if not reports_items:
            logger.error("Reports folder not found in the shared folder")
            return
            
        reports_id = reports_items[0]['id']
        
        # Find active folder
        active_query = f"name='active' and mimeType='application/vnd.google-apps.folder' and '{reports_id}' in parents and trashed=false"
        active_results = service.files().list(q=active_query, spaces='drive', fields='files(id)').execute()
        active_items = active_results.get('files', [])
        
        if not active_items:
            logger.error("Active folder not found in the reports folder")
            return
            
        active_folder_id = active_items[0]['id']
        
        # Find the setting folder in the active folder
        setting_query = f"name='{setting_id}' and mimeType='application/vnd.google-apps.folder' and '{active_folder_id}' in parents and trashed=false"
        setting_results = service.files().list(q=setting_query, spaces='drive', fields='files(id)').execute()
        setting_items = setting_results.get('files', [])
        
        if not setting_items:
            logger.info(f"Setting folder {setting_id} not found in the active folder")
            return
            
        source_folder_id = setting_items[0]['id']
        
        # Make sure deleted folder exists
        deleted_query = f"name='deleted' and mimeType='application/vnd.google-apps.folder' and '{reports_id}' in parents and trashed=false"
        deleted_results = service.files().list(q=deleted_query, spaces='drive', fields='files(id)').execute()
        deleted_items = deleted_results.get('files', [])
        
        if not deleted_items:
            # Create deleted folder
            deleted_id = create_folder(service, 'deleted', reports_id)
        else:
            deleted_id = deleted_items[0]['id']
        
        # Update the parent of the source folder to move it directly under deleted folder
        service.files().update(
            fileId=source_folder_id,
            addParents=deleted_id,
            removeParents=active_folder_id,
            fields='id, parents'
        ).execute()
        
        logger.info(f"Moved report folder for setting ID {setting_id} to deleted")
    
    except Exception as e:
        logger.error(f"Error moving report for setting ID {setting_id}: {str(e)}")
        raise
