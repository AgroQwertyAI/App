from pydantic import BaseModel

class GoogleDriveConfig(BaseModel):
    service_account_json: dict
    shared_folder_name: str

class YandexDiskConfig(BaseModel):
    token: str
    shared_folder_name: str