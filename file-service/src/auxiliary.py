import os
from src.schemas import CronJob, CronArgs
from src.settings import generator_service_url
import aiohttp
from fastapi import HTTPException
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from google.oauth2 import service_account


def get_command(job: CronJob) -> str:
    return f"uv run {os.path.dirname(__file__)}/scripts/save.py {job.folder_name} {job.format} {job.chat_id} {job.type}"


def get_schedule(job: CronJob) -> str:
    return f"{job.minute} {job.hour} {job.day_of_month} {job.month} {job.day_of_week}"


def get_full_record(job: CronJob) -> str:
    return f"{get_schedule(job)} {get_command(job)}"


async def get_data(cron_args: CronArgs) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{generator_service_url}/api/services/generate_table?chat_id={cron_args.chat_id}&format={cron_args.format}") as response:
            if response.status != 200:
                raise HTTPException(500, detail=f"Failed to generate table: {response.status}")
            return await response.text()


def save_data_to_filesystem(cron_args: CronArgs, data: str):
    current_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    with open(f"{os.path.dirname(__file__)}/{cron_args.folder_name}/{current_time}.{cron_args.format}", "w") as f:
        f.write(data)


def save_data_to_drive(cron_args: CronArgs, data: str):
        current_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        filename = f"{current_time}.{cron_args.format}"
        
        # Path to service account credentials
        credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')
        
        # Authenticate with Google Drive
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Build the Drive service
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Find or create the target folder
        folder_id = None
        query = f"name='{cron_args.folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        
        if not results['files']:
            # Create the folder if it doesn't exist
            folder_metadata = {
                'name': cron_args.folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
        else:
            folder_id = results['files'][0]['id']
        
        # Determine MIME type based on format
        mime_type = 'text/csv' if format == 'csv' else 'application/xml'
        
        # Create file metadata
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        # Upload the file
        media = MediaInMemoryUpload(data.encode('utf-8'), mimetype=mime_type)
        drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()