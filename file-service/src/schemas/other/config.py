from pydantic import BaseModel

class GoogleDriveConfig(BaseModel):
    service_account_json: dict
    shared_folder_name: str
