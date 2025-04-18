from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaInMemoryUpload, HttpRequest
from google.oauth2 import service_account
from datetime import datetime
from fastapi import HTTPException
import json
import pandas as pd
import base64
import io
from src.session import get_session
from pathlib import Path
import tempfile
import os
import asyncio
import httpx
from src.auxiliary.logging import log_info
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
CONFIG_FILE_GOOGLE_DRIVE = OAUTH_CONFIG_DIR / "google_drive_credentials.json"

def get_google_drive_config():
    """Get the Google Drive credentials from the configuration file."""
    try:
        if not CONFIG_FILE_GOOGLE_DRIVE.exists():
            log_info("Google Drive credentials file not found", 'error')
            raise HTTPException(status_code=404, detail="Google Drive credentials file not found")
        
        with open(CONFIG_FILE_GOOGLE_DRIVE, "r") as f:
            data = json.load(f)
            return data
    except Exception:
        log_info(f"Error getting Google Drive config", 'error')
        raise

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

def create_folder(service, name, parent_id=None) -> HttpRequest:
    """Create a folder in Google Drive and return http request"""
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    folder = service.files().create(body=file_metadata, fields='id')
    return folder

def upload_file(service, file_content, filename, parent_id, mime_type) -> HttpRequest:
    """Upload a file to Google Drive and return http request"""
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
    )
    
    return file

def find_shared_folder(service):
    """Find a folder that has been shared with the service account"""
    # Get folder name from config, or use default
    config = get_google_drive_config()
    folder_name: str = config["shared_folder_name"]

    if "drive/folders/" in folder_name:
        names = [name for name in folder_name.split("/") if len(name) > 0]
        return names[-1]
    
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])

    if not items:
        folder_id = folder_name
        return folder_id
        
    return items[0]['id']

async def save_google_drive_report(setting: dict) -> str:
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
        
        # Initialize Google Drive service
        service = get_drive_service()
        
        # Find the shared agriculture folder
        base_folder_id = find_shared_folder(service)
        if not base_folder_id:
            log_info("Cannot proceed without access to the shared folder", 'error')
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
                current_parent_id = create_folder(service, folder_name, current_parent_id).execute()['id']
        
        report_dir_id = current_parent_id
        messages_dir_id = create_folder(service, "messages", report_dir_id).execute()['id']
        
        # Generate xlsx file
        df = pd.DataFrame(aggregated_data)

        # Create base64 encoded file content
        file = ""
        if report_format == "xlsx":
            file_content = convert_dataframe_to_bytes_xlsx(df)
            
            # Upload to Google Drive directly from memory
            memory_file = io.BytesIO(file_content)
            upload_file(
                service, 
                memory_file, 
                f"report.{report_format}", 
                report_dir_id,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ).execute()
            
            # Create base64 encoded version for database
            file = f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{base64.b64encode(file_content).decode('utf-8')}"
        
        # 4. Create a new Report record
        report_id = save_report_to_db(setting_id, file, conn)
        
        messages_by_sender = group_messages_by_sender(pending_messages)

        async with httpx.AsyncClient() as client:
            requests = []

            for sender_id, sender_messages in messages_by_sender.items():
                requests.append(
                    client.post(
                        "https://www.googleapis.com/drive/v3/files", 
                        headers={
                            "Authorization": f"Bearer {service._http.credentials.token}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "name": str(sender_id), 
                            "parents": [messages_dir_id],
                            "mimeType": "application/vnd.google-apps.folder"
                        }
                    )
                )

            user_folders = await asyncio.gather(*requests)
            user_folders_ids = [resp.json()['id'] for resp in user_folders]



        user_requests: dict[str, list[httpx.Request]] = {}
        async with httpx.AsyncClient() as client:
            for user_folder_id, sender_messages in zip(user_folders_ids, messages_by_sender.values()):
                user_requests[user_folder_id] = []

                for i, message in enumerate(sender_messages):
                    user_requests[user_folder_id].append(
                        client.post(
                            "https://www.googleapis.com/drive/v3/files", 
                            headers={
                                "Authorization": f"Bearer {service._http.credentials.token}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "name": str(i), 
                                "parents": [user_folder_id],
                                "mimeType": "application/vnd.google-apps.folder"
                            }
                        )
                    )

            user_message_id_to_folder_id: dict[str, list[str]] = {}

            for user_folder_id, requests in user_requests.items():
                message_folders = await asyncio.gather(*requests)
                message_folders_ids = [resp.json()['id'] for resp in message_folders]

                user_message_id_to_folder_id[user_folder_id] = message_folders_ids



        #create images folder for every message
        async with httpx.AsyncClient() as client:
            image_folder_requests: list[httpx.Request] = []

            for i, (sender_id, sender_messages) in enumerate(messages_by_sender.items()):
                # Create user directory on Google Drive
                user_dir_id = user_folders_ids[i]
                
                # 4.1 Save each message separately
                for message, message_folder_id in zip(sender_messages, user_message_id_to_folder_id[user_dir_id]):
                    # Save individual message text

                    image_folder_requests.append(client.post(
                            "https://www.googleapis.com/drive/v3/files", 
                            headers={
                                "Authorization": f"Bearer {service._http.credentials.token}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "name": "images", 
                                "parents": [message_folder_id],
                                "mimeType": "application/vnd.google-apps.folder"
                            }
                        )
                    )

            image_folders = await asyncio.gather(*image_folder_requests)
            message_id_to_image_folder_id = {}
            
            j = 0
            for i ,(sender_id, sender_messages) in enumerate(messages_by_sender.items()):
                user_dir_id = user_folders_ids[i]
                
                # 4.1 Save each message separately
                for message, message_folder_id in zip(sender_messages, user_message_id_to_folder_id[user_dir_id]):
                    # Save individual message text

                    message_id_to_image_folder_id[message_folder_id] = image_folders[j].json()['id']
                    j += 1

        async with httpx.AsyncClient() as client:
            requests = []
            log_info("uploading user_messages", 'info')

            # Process each sender's messages as a group
            for i, (sender_id, sender_messages) in enumerate(messages_by_sender.items()):
                log_info(f"uploading messages for user {sender_id}", 'info')
                # Create user directory on Google Drive
                user_dir_id = user_folders_ids[i]
                
                # 4.1 Save each message separately
                for i, (message, message_folder_id) in enumerate(zip(sender_messages, user_message_id_to_folder_id[user_dir_id])):
                    # Save individual message text
                    requests.append(client.post(
                        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                        headers={
                            "Authorization": f"Bearer {service._http.credentials.token}",
                            "Content-Type": "multipart/related; boundary=boundary",
                        },
                        content=(
                            b"--boundary\r\n"
                            b"Content-Type: application/json\r\n\r\n" +
                            f'{{"name": "text.txt", "parents": ["{message_folder_id}"], "mimeType": "text/plain"}}\r\n'.encode('utf-8') +
                            b"--boundary\r\n"
                            b"Content-Type: text/plain\r\n\r\n" +
                            message['original_message_text'].encode('utf-8') + 
                            b"\r\n--boundary--"
                        ),
                    ))

                    requests.append(client.post(
                        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                        headers={
                            "Authorization": f"Bearer {service._http.credentials.token}",
                            "Content-Type": "multipart/related; boundary=boundary",
                        },
                        content=(
                            b"--boundary\r\n"
                            b"Content-Type: application/json\r\n\r\n" +
                            f'{{"name": "formatted_text.json", "parents": ["{message_folder_id}"], "mimeType": "application/json"}}\r\n'.encode('utf-8') +
                            b"--boundary\r\n"
                            b"Content-Type: application/json\r\n\r\n" +
                            message['formatted_message_text'].encode('utf-8') + 
                            b"\r\n--boundary--"
                        ),
                    ))

                    # 4.3 save images
                    images = json.loads(message["images"]) if message["images"] else {"images": []}
                    
                    # Save each image for this message
                    for j, image in enumerate(images["images"]):
                        # Save the base64 encoded image with index to keep them separate
                        try:
                            image_binary, image_extension = get_image_binary_from_base64(image)
                            
                            # Upload image directly from memory with index suffix
                            mime_type = f"image/{image_extension}" if image_extension != "jpg" else "image/jpeg"
                            
                            image_request = client.post(
                                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                                headers={
                                    "Authorization": f"Bearer {service._http.credentials.token}",
                                    "Content-Type": "multipart/related; boundary=boundary",
                                },
                                content=(
                                    b"--boundary\r\n"
                                    b"Content-Type: application/json\r\n\r\n" +
                                    f'{{"name": "{str(j)}.{image_extension}", "parents": ["{message_id_to_image_folder_id[message_folder_id]}"], "mimeType": "{mime_type}"}}\r\n'.encode('utf-8') +
                                    b"--boundary\r\n" +
                                    f"Content-Type: {mime_type}\r\n\r\n".encode('utf-8') +
                                    image_binary +
                                    b"\r\n--boundary--"
                                ),
                            )

                            requests.append(image_request)

                        except Exception as e:
                            log_info(f"Error saving image: {e}", 'error')

                    # save message to db
                    save_message_report_to_db(message, report_id, conn)

            await asyncio.gather(*requests)

        # 4.4 Aggregate formatted_message_text JSON objects
        aggregated_json = get_aggregated_json_from_messages(pending_messages)
        
        # Save aggregated formatted text
        upload_file(
            service,
            json.dumps(aggregated_json).encode('utf-8'),
            "formatted_text.json",
            report_dir_id,
            'application/json'
        ).execute()
        
        # 6. Delete previous messages_pending for this setting
        delete_pending_messages(setting_id, conn)
            
        return file

def move_google_drive_report_to_deleted(setting_id: int):
    try:
        # Initialize Google Drive service
        service = get_drive_service()
        
        # Find the shared agriculture folder
        base_folder_id = find_shared_folder(service)
        if not base_folder_id:
            log_info("Cannot proceed without access to the shared folder", 'error')
            return
        
        # Find reports folder in the shared folder
        reports_query = f"name='reports' and mimeType='application/vnd.google-apps.folder' and '{base_folder_id}' in parents and trashed=false"
        reports_results = service.files().list(q=reports_query, spaces='drive', fields='files(id)').execute()
        reports_items = reports_results.get('files', [])
        
        if not reports_items:
            log_info("Reports folder not found in the shared folder", 'error')
            return
            
        reports_id = reports_items[0]['id']
        
        # Find active folder
        active_query = f"name='active' and mimeType='application/vnd.google-apps.folder' and '{reports_id}' in parents and trashed=false"
        active_results = service.files().list(q=active_query, spaces='drive', fields='files(id)').execute()
        active_items = active_results.get('files', [])
        
        if not active_items:
            log_info("Active folder not found in the reports folder", 'error')
            return
            
        active_folder_id = active_items[0]['id']
        
        # Find the setting folder in the active folder
        setting_query = f"name='{setting_id}' and mimeType='application/vnd.google-apps.folder' and '{active_folder_id}' in parents and trashed=false"
        setting_results = service.files().list(q=setting_query, spaces='drive', fields='files(id)').execute()
        setting_items = setting_results.get('files', [])
        
        if not setting_items:
            log_info(f"Setting folder {setting_id} not found in the active folder", 'error')
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
        
        log_info(f"Moved report folder for setting ID {setting_id} to deleted", 'info')
    
    except Exception as e:
        log_info(f"Error moving report for setting ID {setting_id}: {e}", 'error')
        raise
