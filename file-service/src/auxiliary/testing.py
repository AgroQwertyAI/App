from src.schemas.endpoints.message_pending import MessagePendingPost
from datetime import datetime, timezone, timedelta
from src.session import get_session
from src.generating_reports.systems.google_drive import get_drive_service, find_shared_folder, create_folder, upload_file
from src.generating_reports.helper import get_pending_messages, aggregate_messages, convert_dataframe_to_bytes_xlsx
import pandas as pd
from sqlite3 import Connection
from src.generating_reports.systems.yandex_disk import get_yandex_disk_config, get_yandex_disk_folder_path
import yadisk
import io
from src.auxiliary.logging import log_info
import httpx
import asyncio

def get_message_number(sender_name: str, setting_id: int) -> int:
    """
    Count the number of messages from a specific sender_id in the database and add 1
    
    Args:
        sender_id: The ID of the message sender
        
    Returns:
        int: The next message number for this sender
    """
    with get_session() as conn:
        cursor = conn.cursor()
        
        # Count all messages with this sender_id
        cursor.execute(
            "SELECT COUNT(*) FROM messages_pending WHERE sender_name = ? AND setting_id = ?", 
            (sender_name, setting_id)
        )
        count = cursor.fetchone()[0]
        
        # Add 1 to get the new message number
        return count + 1

async def update_google_drive(message: MessagePendingPost, setting_id: int, conn: Connection):
    # Use Moscow time zone (UTC+3)
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz)
    formatted_date_message = now.strftime("%M%H%d%m%Y")
    
    # Get the message number for this sender
    message_number = get_message_number(message.sender_name, setting_id)

    file_name = f"{message.sender_name}_{message_number}_{formatted_date_message}.txt"
    text = message.original_message_text
    
    # Initialize Google Drive service
    service = get_drive_service()
    
    # Find the shared folder
    base_folder_id = find_shared_folder(service)
    if not base_folder_id:
        raise Exception("Cannot access the shared folder")
    
    # Check if 'qwerty' folder exists, create if not
    query = f"name='qwerty' and mimeType='application/vnd.google-apps.folder' and '{base_folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if items:
        qwerty_folder_id = items[0]['id']
    else:
        # Create 'qwerty' folder if it doesn't exist
        qwerty_folder_id = create_folder(service, 'qwerty', base_folder_id).execute()['id']
    
    # Check for existing Excel files in the qwerty folder and delete them
    excel_query = f"mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and '{qwerty_folder_id}' in parents and trashed=false"
    excel_results = service.files().list(q=excel_query, spaces='drive', fields='files(id, name)').execute()
    excel_items = excel_results.get('files', [])
    
    # Delete any existing Excel files
    for excel_file in excel_items:
        service.files().delete(fileId=excel_file['id']).execute()
    
    # Upload files asynchronously
    async with httpx.AsyncClient() as client:
        requests = []
        
        # Text file upload request
        requests.append(client.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers={
                "Authorization": f"Bearer {service._http.credentials.token}",
                "Content-Type": "multipart/related; boundary=boundary",
            },
            content=(
                "--boundary\r\n"
                "Content-Type: application/json\r\n\r\n"
                f'{{"name": "{file_name}", "parents": ["{qwerty_folder_id}"], "mimeType": "text/plain"}}\r\n'
                "--boundary\r\n"
                "Content-Type: text/plain\r\n\r\n"
                f"{text}\r\n"
                "--boundary--"
            ),
        ))

        pending_messages = get_pending_messages(setting_id, conn)
        agreggated_data = aggregate_messages(pending_messages)

        df = pd.DataFrame(agreggated_data)
        xlsx_bytes = convert_dataframe_to_bytes_xlsx(df)

        formatted_date_xlsx = now.strftime("%H%d%m%Y")
        xlsx_file_name = f"{formatted_date_xlsx}_qwerty.xlsx"

        # Excel file upload request
        requests.append(client.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers={
                "Authorization": f"Bearer {service._http.credentials.token}",
                "Content-Type": "multipart/related; boundary=boundary",
            },
            content=(
                "--boundary\r\n"
                "Content-Type: application/json\r\n\r\n"
                f'{{"name": "{xlsx_file_name}", "parents": ["{qwerty_folder_id}"], "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}}\r\n'
                "--boundary\r\n"
                "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
                f"{xlsx_bytes}\r\n"
                "--boundary--"
            ),
        ))
        
        # Wait for all uploads to complete
        await asyncio.gather(*requests)

async def update_yandex_disk(message: MessagePendingPost, setting_id: int, conn: Connection):
    # Use Moscow time zone (UTC+3)
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz)
    formatted_date = now.strftime("%M%H%d%m%Y")
    
    # Get the message number for this sender
    message_number = get_message_number(message.sender_name, setting_id)

    file_name = f"{message.sender_name}_{message_number}_{formatted_date}.txt"
    text = message.original_message_text
    
    yandex_config = get_yandex_disk_config()
    if not yandex_config or not yandex_config.get("token"):
        raise Exception("Cannot access Yandex Disk token")
    
    # Initialize Yandex Disk async client
    y = yadisk.AsyncClient(token=yandex_config["token"])
    
    # Get shared folder name from config
    shared_folder_name = get_yandex_disk_folder_path()
    base_path = f"/{shared_folder_name}"
    
    # Check if 'qwerty' folder exists, create if not
    qwerty_path = f"{base_path}/qwerty"
    
    # Use synchronous client for checking existence
    sync_y = yadisk.YaDisk(token=yandex_config["token"])
    if not sync_y.exists(qwerty_path):
        await y.mkdir(qwerty_path)
    
    # Check for existing Excel files in the qwerty folder and delete them
    requests = []
    for item in sync_y.listdir(qwerty_path):
        if item["mime_type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            requests.append(y.remove(item["path"]))
    
    if requests:
        await asyncio.gather(*requests)
    
    requests = []
    
    # Upload the text file to Yandex Disk
    text_buffer = io.BytesIO(text.encode('utf-8'))
    requests.append(y.upload(text_buffer, f"{qwerty_path}/{file_name}"))

    # Get pending messages and create Excel report
    pending_messages = get_pending_messages(setting_id, conn)
    agreggated_data = aggregate_messages(pending_messages)

    df = pd.DataFrame(agreggated_data)
    xlsx_bytes = convert_dataframe_to_bytes_xlsx(df)

    formatted_date_xlsx = now.strftime("%H%d%m%Y")
    xlsx_file_name = f"{formatted_date_xlsx}_qwerty.xlsx"

    # Upload Excel file to Yandex Disk
    xlsx_buffer = io.BytesIO(xlsx_bytes)
    requests.append(y.upload(xlsx_buffer, f"{qwerty_path}/{xlsx_file_name}"))
    
    # Wait for all uploads to complete
    await asyncio.gather(*requests)