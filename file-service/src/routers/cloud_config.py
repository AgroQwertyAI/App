from fastapi import APIRouter, HTTPException, Body
import os
import json
from src.generating_reports.systems.yandex_disk import get_yandex_disk_config, CONFIG_FILE_YANDEX_DISK, OAUTH_CONFIG_DIR
from src.schemas.other.config import GoogleDriveConfig, YandexDiskConfig
from src.generating_reports.systems.google_drive import get_google_drive_config, CONFIG_FILE_GOOGLE_DRIVE

cloud_config_router = APIRouter(tags=["cloud_config"])


# Create config directory if it doesn't exist
os.makedirs(OAUTH_CONFIG_DIR, exist_ok=True)

@cloud_config_router.get(
    "/yandex-disk-credentials", 
    response_model=YandexDiskConfig, 
    status_code=200,
    responses={
        404: {
            "description": "No Yandex OAuth token found"
        }
    }
)
async def get_yandex_config():
    """Get the current Yandex OAuth token and shared folder link."""
    # Get the full config data
    config_data = get_yandex_disk_config()
    
    # If no config data exists or token is missing
    if not config_data or "token" not in config_data or not config_data["token"]:
        raise HTTPException(status_code=404, detail="No Yandex OAuth token found")
    
    # Return the config using the YandexDiskConfig model
    return YandexDiskConfig(
        token=config_data["token"],
        shared_folder_name=config_data.get("shared_folder_name", "")
    )


@cloud_config_router.post(
    "/yandex-disk-credentials", 
    response_model=YandexDiskConfig, 
    status_code=201
)
async def set_yandex_disk_config(config: YandexDiskConfig = Body(...)):
    """Set a new Yandex OAuth token and shared folder link."""
    # Create the config directory and any parent directories if they don't exist
    os.makedirs(os.path.dirname(CONFIG_FILE_YANDEX_DISK), exist_ok=True)
    
    with open(CONFIG_FILE_YANDEX_DISK, "w") as f:
        json.dump({
            "token": config.token,
            "shared_folder_name": config.shared_folder_name
        }, f, indent=2)
    return config


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
    
    # Create the config directory and any parent directories if they don't exist
    os.makedirs(os.path.dirname(CONFIG_FILE_GOOGLE_DRIVE), exist_ok=True)
    
    with open(CONFIG_FILE_GOOGLE_DRIVE, "w") as f:
        json.dump(credentials, f, indent=2)
    
    return google_drive_config

