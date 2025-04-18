from src.schemas.endpoints.message_pending import MessagePendingPost
from datetime import datetime, timezone, timedelta
from src.session import get_session
from src.generating_reports.systems.google_drive import get_drive_service, find_shared_folder
from src.generating_reports.helper import get_pending_messages, aggregate_messages, convert_dataframe_to_bytes_xlsx
import pandas as pd
from src.generating_reports.systems.yandex_disk import get_yandex_disk_config, get_yandex_disk_folder_path
import yadisk
import io
import httpx

def get_message_number(sender_id: str, setting_id: int) -> int:
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
            "SELECT COUNT(*) FROM messages_pending WHERE sender_id = ? AND setting_id = ?", 
            (sender_id, setting_id)
        )
        count = cursor.fetchone()[0]
        
        return count 

def update_google_drive(message: MessagePendingPost, setting_id: int):
    # Use Moscow time zone (UTC+3)
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz)
    
    # Get the message number for this sender
    message_number = get_message_number(message.sender_id, setting_id)

    file_name = f"{message.sender_name}_{message_number}_{message.extra.get('datetime', now.strftime('%M%H%d%m%Y'))}.txt"
    text = message.original_message_text
    
    # Initialize Google Drive service
    service = get_drive_service()
    
    # Find the shared folder
    qwerty_folder_id = find_shared_folder(service)
    if not qwerty_folder_id:
        raise Exception("Cannot access the shared folder")

    with get_session() as conn:
        pending_messages = get_pending_messages(setting_id, conn)
    
    agreggated_data = aggregate_messages(pending_messages)

    df = pd.DataFrame(agreggated_data)
    xlsx_bytes = convert_dataframe_to_bytes_xlsx(df)

    formatted_date_xlsx = now.strftime("%H%d%m%Y")
    xlsx_file_name = f"{formatted_date_xlsx}_qwerty.xlsx"

    # Check for existing Excel files in the qwerty folder and delete them
    excel_query = f"mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and '{qwerty_folder_id}' in parents and trashed=false"
    excel_results = service.files().list(q=excel_query, spaces='drive', fields='files(id, name)').execute()
    excel_items = excel_results.get('files', [])
    
    with httpx.Client() as client:
        for excel_file in excel_items:
            client.delete(
                f"https://www.googleapis.com/drive/v3/files/{excel_file['id']}",
                headers={"Authorization": f"Bearer {service._http.credentials.token}"}
            )
        
        # Text file upload request
        client.post(
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
        )

        # Construct multipart body as bytes
        boundary = b"boundary"
        metadata = (
            f'{{"name": "{xlsx_file_name}", "parents": ["{qwerty_folder_id}"], '
            f'"mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}}'
        ).encode("utf-8")

        # Build each part of the multipart content
        body = (
            b"--" + boundary + b"\r\n"
            b"Content-Type: application/json\r\n\r\n"
            + metadata + b"\r\n"
            b"--" + boundary + b"\r\n"
            b"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
            + xlsx_bytes + b"\r\n"
            b"--" + boundary + b"--"
        )

        client.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers={
                "Authorization": f"Bearer {service._http.credentials.token}",
                "Content-Type": "multipart/related; boundary=boundary",
            },
            content=body
        )


def update_yandex_disk(message: MessagePendingPost, setting_id: int):
    # Use Moscow time zone (UTC+3)
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz)
    
    # Get the message number for this sender
    message_number = get_message_number(message.sender_id, setting_id)

    file_name = f"{message.sender_name}_{message_number}_{message.extra.get('datetime', now.strftime('%M%H%d%m%Y'))}.txt"
    text = message.original_message_text
    
    yandex_config = get_yandex_disk_config()
    if not yandex_config or not yandex_config.get("token"):
        raise Exception("Cannot access Yandex Disk token")
    
    # Get shared folder name from config
    shared_folder_name = get_yandex_disk_folder_path()
    base_path = f"/{shared_folder_name}"
    
    # Check if 'qwerty' folder exists, create if not
    qwerty_path = f"{base_path}/qwerty"
    
    # Use synchronous client for checking existence
    sync_y = yadisk.YaDisk(token=yandex_config["token"])
    if not sync_y.exists(qwerty_path):
        sync_y.mkdir(qwerty_path)
    
    for item in sync_y.listdir(qwerty_path):
        if item["mime_type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            sync_y.remove(item["path"])
    
    
    # Upload the text file to Yandex Disk
    text_buffer = io.BytesIO(text.encode('utf-8'))
    sync_y.upload(text_buffer, f"{qwerty_path}/{file_name}")

    # Get pending messages and create Excel report
    with get_session() as conn:
        pending_messages = get_pending_messages(setting_id, conn)
        
    agreggated_data = aggregate_messages(pending_messages)

    df = pd.DataFrame(agreggated_data)
    xlsx_bytes = convert_dataframe_to_bytes_xlsx(df)

    formatted_date_xlsx = now.strftime("%H%d%m%Y")
    xlsx_file_name = f"{formatted_date_xlsx}_qwerty.xlsx"

    # Upload Excel file to Yandex Disk
    xlsx_buffer = io.BytesIO(xlsx_bytes)
    sync_y.upload(xlsx_buffer, f"{qwerty_path}/{xlsx_file_name}")
