from src.schemas.endpoints.message_pending import MessagePendingPost
from datetime import datetime, timezone, timedelta
from src.session import get_session
from src.generating_reports.systems.google_drive import get_drive_service, find_shared_folder, create_folder, upload_file
from src.generating_reports.helper import get_pending_messages, aggregate_messages, convert_dataframe_to_bytes_xlsx
import pandas as pd
from sqlite3 import Connection

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

def update_google_drive(message: MessagePendingPost, setting_id: int, conn: Connection):
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
    
    # Upload the file to the qwerty folder
    upload_file(
        service,
        text,
        file_name,
        qwerty_folder_id,
        'text/plain'
    ).execute()

    pending_messages = get_pending_messages(setting_id, conn)
    agreggated_data = aggregate_messages(pending_messages)

    df = pd.DataFrame(agreggated_data)
    xlsx_bytes = convert_dataframe_to_bytes_xlsx(df)

    formatted_date_xlsx = now.strftime("%H%d%m%Y")
    xlsx_file_name = f"{formatted_date_xlsx}_qwerty.xlsx"

    upload_file(
        service,
        xlsx_bytes,
        xlsx_file_name,
        qwerty_folder_id,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ).execute()

def update_yandex_disk(message: MessagePendingPost, setting_id: int, conn: Connection):
    # Use Moscow time zone (UTC+3)
    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz)
    formatted_date = now.strftime("%M%H%d%m%Y")
    
    # Get the message number for this sender
    message_number = get_message_number(message.sender_name, setting_id)

    file_name = f"{message.sender_name}_{message_number}_{formatted_date}.txt"
    text = message.original_message_text
    
    # Get Yandex Disk config and token
    from src.generating_reports.systems.yandex_disk import get_yandex_disk_config
    import yadisk
    import io
    
    yandex_config = get_yandex_disk_config()
    if not yandex_config or not yandex_config.get("token"):
        raise Exception("Cannot access Yandex Disk token")
    
    # Initialize Yandex Disk client
    y = yadisk.YaDisk(token=yandex_config["token"])
    
    # Get shared folder name from config
    shared_folder_name = yandex_config["shared_folder_name"]
    base_path = f"/{shared_folder_name}"
    
    # Check if 'qwerty' folder exists, create if not
    qwerty_path = f"{base_path}/qwerty"
    if not y.exists(qwerty_path):
        y.mkdir(qwerty_path)
    
    # Check for existing Excel files in the qwerty folder and delete them
    for item in y.listdir(qwerty_path):
        if item["mime_type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            y.remove(item["path"])
    
    # Upload the text file to Yandex Disk
    text_buffer = io.BytesIO(text.encode('utf-8'))
    y.upload(text_buffer, f"{qwerty_path}/{file_name}")

    # Get pending messages and create Excel report
    pending_messages = get_pending_messages(setting_id, conn)
    agreggated_data = aggregate_messages(pending_messages)

    df = pd.DataFrame(agreggated_data)
    xlsx_bytes = convert_dataframe_to_bytes_xlsx(df)

    formatted_date_xlsx = now.strftime("%H%d%m%Y")
    xlsx_file_name = f"{formatted_date_xlsx}_qwerty.xlsx"

    # Upload Excel file to Yandex Disk
    xlsx_buffer = io.BytesIO(xlsx_bytes)
    y.upload(xlsx_buffer, f"{qwerty_path}/{xlsx_file_name}")