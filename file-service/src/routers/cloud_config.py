from fastapi import APIRouter, HTTPException, Body
import os
import json
from src.generating_reports.systems.yandex_disk import get_oauth_token
from src.generating_reports.systems.yandex_disk import OAUTH_CONFIG_FILE, OAUTH_CONFIG_DIR
from src.schemas.other.config import GoogleDriveConfig
from src.generating_reports.systems.google_drive import get_google_drive_config

cloud_config_router = APIRouter(tags=["cloud_config"])

# Create config directory if it doesn't exist
os.makedirs(OAUTH_CONFIG_DIR, exist_ok=True)

# Define Google Drive config file path
GOOGLE_DRIVE_CONFIG_FILE = OAUTH_CONFIG_DIR / "google_drive_credentials.json"


@cloud_config_router.get(
    "/yandex-oauth-token", 
    response_model=str, 
    status_code=200,
    responses={
        404: {
            "description": "No Yandex OAuth token found"
        }
    }
)
async def get_yandex_oauth_token():
    """Get the current Yandex OAuth token."""
    token = get_oauth_token()
    if not token:
        raise HTTPException(status_code=404, detail="No Yandex OAuth token found")
    return token


@cloud_config_router.post(
    "/yandex-oauth-token", 
    response_model=str, 
    status_code=201
)
async def set_yandex_oauth_token(token: str = Body(...)):
    """Set a new Yandex OAuth token."""
    with open(OAUTH_CONFIG_FILE, "w") as f:
        json.dump({"token": token}, f)
    return token


@cloud_config_router.get(
    "/google-drive-credentials",
    status_code=200,
    response_model=GoogleDriveConfig,
    responses={
        404: {"description": "No Google Drive credentials found"}
    }
)
async def get_google_drive_info():
    """Get the current Google Drive credentials and shared folder name."""
    config = get_google_drive_config()
    return config


@cloud_config_router.post(
    "/google-drive-credentials",
    status_code=201,
    response_model=GoogleDriveConfig
)
async def set_google_drive_info(
    google_drive_config: GoogleDriveConfig = Body(...)
):
    """Set new Google Drive credentials and shared folder name."""
    credentials = {
        "service_account_json": google_drive_config.service_account_json,
        "shared_folder_name": google_drive_config.shared_folder_name
    }
    
    with open(GOOGLE_DRIVE_CONFIG_FILE, "w") as f:
        json.dump(credentials, f, indent=2)
    
    return google_drive_config

