from fastapi import APIRouter, Query, HTTPException
from src.schemas.endpoints.setting import SettingGet, SettingPost, SettingPut
from src.session import get_session
import json
from src.auxiliary.cron import create_cron_job, delete_cron_job
import logging
from src.generating_reports.systems.filesystem import move_local_report_to_deleted
from src.generating_reports.systems.yandex_disk import move_yandex_disk_report_to_deleted
from src.generating_reports.systems.google_drive import move_google_drive_report_to_deleted

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

settings_router = APIRouter(tags=["settings"])


@settings_router.get(
    "/settings", 
    response_model=list[SettingGet], 
    description="Get all settings", 
    status_code=200,
)
async def get_settings(
    offset: int = Query(default=0, description="The offset of the settings"), 
    limit: int = Query(default=10, description="The limit of the settings"),
    show_deleted: bool = Query(default=False, description="Show deleted settings"),
):
    with get_session() as conn:
        cursor = conn.cursor()
        
        # Build the query based on whether to show deleted settings
        query = "SELECT * FROM settings"
        if not show_deleted:
            query += " WHERE deleted = 0"
            
        # Add limit and offset
        query += f" LIMIT {limit} OFFSET {offset}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Convert SQLite rows to SettingGet objects
        result = []
        for row in rows:
            # Parse JSON strings from database
            send_to_data = json.loads(row['send_to']) if row['send_to'] else []
            extra_data = json.loads(row['extra']) if row['extra'] else {}
            
            # Get each field and convert to appropriate type
            setting = SettingGet(
                setting_id=row['setting_id'],
                setting_name=row['setting_name'],
                setting_description=row['setting_description'],
                format_report=row['format_report'],
                type=row['type'],
                send_to=send_to_data,
                minute=row['minute'],
                hour=row['hour'],
                day_of_month=row['day_of_month'],
                month=row['month'],
                day_of_week=row['day_of_week'],
                deleted=bool(row['deleted']),
                extra=extra_data
            )
            result.append(setting)
            
        return result


@settings_router.post(
    "/setting", 
    response_model=SettingGet, 
    description="Create a new setting", 
    status_code=201,
)
async def post_setting(
    setting: SettingPost
):
    # Save setting to database
    with get_session() as conn:
        cursor = conn.cursor()
        
        # Prepare the insert query
        query = """
        INSERT INTO settings (
            setting_name, setting_description, format_report, type, 
            send_to, minute, hour, day_of_month, month, day_of_week, 
            deleted, extra
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Convert any JSON fields to strings
        send_to_json = json.dumps(
            [s.model_dump() for s in setting.send_to] 
            if isinstance(setting.send_to, list) else setting.send_to
        )
        extra_json = json.dumps(setting.extra)
        
        # Execute query
        cursor.execute(query, (
            setting.setting_name,
            setting.setting_description,
            setting.format_report,
            setting.type,
            send_to_json,
            setting.minute,
            setting.hour,
            setting.day_of_month,
            setting.month,
            setting.day_of_week,
            False,  # Not deleted by default
            extra_json
        ))
        
        # Get the inserted ID
        setting_id = cursor.lastrowid
        
        # Create a cron job
        try:
            create_cron_job(setting_id, setting)
            logger.info(f"Cron job created for setting ID: {setting_id}")
        except Exception as e:
            # If cron job creation fails, we should rollback transaction
            logger.error(f"Failed to create cron job: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create cron job")
        
        # Return the created setting with its ID
        return SettingGet(
            setting_id=setting_id,
            setting_name=setting.setting_name,
            setting_description=setting.setting_description,
            format_report=setting.format_report,
            type=setting.type,
            send_to=setting.send_to,
            minute=setting.minute,
            hour=setting.hour,
            day_of_month=setting.day_of_month,
            month=setting.month,
            day_of_week=setting.day_of_week,
            deleted=False,
            extra=setting.extra
        )


@settings_router.put(
    "/setting/{id}", 
    response_model=SettingGet, 
    status_code=200,
    description="Update a setting by its id", 
    responses={404:{
        "description": "Setting not found"
    }}
)
async def update_setting(
    id: int, 
    setting_put: SettingPut
):
    with get_session() as conn:
        cursor = conn.cursor()
        
        # First check if the setting exists
        cursor.execute("SELECT * FROM settings WHERE setting_id = ?", (id,))
        existing_setting = cursor.fetchone()
        
        if not existing_setting:
            raise HTTPException(status_code=404, detail=f"Setting with ID {id} not found")
            
        # Convert JSON fields to string
        send_to_json = json.dumps(
            [s.model_dump() for s in setting_put.send_to] 
            if isinstance(setting_put.send_to, list) else setting_put.send_to
        )
        extra_json = json.dumps(setting_put.extra)
        
        # Build the update query
        query = """
        UPDATE settings SET
            setting_name = ?,
            setting_description = ?,
            format_report = ?,
            type = ?,
            send_to = ?,
            minute = ?,
            hour = ?,
            day_of_month = ?,
            month = ?,
            day_of_week = ?,
            extra = ?
        WHERE setting_id = ?
        """
        
        # Execute the update
        cursor.execute(query, (
            setting_put.setting_name,
            setting_put.setting_description,
            setting_put.format_report,
            setting_put.type,
            send_to_json,
            setting_put.minute,
            setting_put.hour,
            setting_put.day_of_month,
            setting_put.month,
            setting_put.day_of_week,
            extra_json,
            id
        ))
        
        # Check if the update was successful
        if cursor.rowcount == 0:
            raise HTTPException(status_code=500, detail="Failed to update setting")
            
        # Delete the existing cron job
        try:
            delete_cron_job(id)
            logger.info(f"Deleted existing cron job for setting ID: {id}")
        except Exception as e:
            logger.error(f"Failed to delete existing cron job: {str(e)}")
            
        # Create a new cron job with updated schedule
        try:
            create_cron_job(id, setting_put)
            logger.info(f"Created new cron job for setting ID: {id}")
        except Exception as e:
            logger.error(f"Failed to create new cron job: {str(e)}")
            
        # Fetch the updated setting
        cursor.execute("SELECT * FROM settings WHERE setting_id = ?", (id,))
        updated_setting = cursor.fetchone()
        
        # Parse JSON strings from database
        send_to_data = json.loads(updated_setting['send_to']) if updated_setting['send_to'] else []
        extra_data = json.loads(updated_setting['extra']) if updated_setting['extra'] else {}
        
        # Return the updated setting
        return SettingGet(
            setting_id=updated_setting['setting_id'],
            setting_name=updated_setting['setting_name'],
            setting_description=updated_setting['setting_description'],
            format_report=updated_setting['format_report'],
            type=updated_setting['type'],
            send_to=send_to_data,
            minute=updated_setting['minute'],
            hour=updated_setting['hour'],
            day_of_month=updated_setting['day_of_month'],
            month=updated_setting['month'],
            day_of_week=updated_setting['day_of_week'],
            deleted=bool(updated_setting['deleted']),
            extra=extra_data
        )


@settings_router.delete(
    "/setting/{id}", 
    response_model=None,
    status_code=204,
    description="Delete a setting by its id", 
    responses={404:{
        "description": "Setting not found"
    }}
)
async def delete_setting(
    id: int
):
    with get_session() as conn:
        cursor = conn.cursor()
        
        # First check if the setting exists
        cursor.execute("SELECT * FROM settings WHERE setting_id = ?", (id,))
        existing_setting = cursor.fetchone()
        
        if not existing_setting:
            raise HTTPException(status_code=404, detail=f"Setting with ID {id} not found")
        
        # Mark the setting as deleted (soft delete)
        cursor.execute("UPDATE settings SET deleted = 1 WHERE setting_id = ?", (id,))
        
        # Check if the update was successful
        if cursor.rowcount == 0:
            raise HTTPException(status_code=500, detail="Failed to delete setting")
        
        # Delete the associated cron job
        try:
            job_deleted = delete_cron_job(id)
            if job_deleted is False:
                logger.info(f"Cron job not found for setting ID: {id}")
            else:
                logger.info(f"Cron job deleted for setting ID: {id}")
        except Exception as e:
            # Log the error but don't fail the request
            logger.error(f"Error deleting cron job for setting {id}: {str(e)}")

        # Move the report folder from active to deleted
        try:
            if existing_setting['type'] == 'filesystem':
                move_local_report_to_deleted(id)
            elif existing_setting['type'] == 'yandex-disk':
                move_yandex_disk_report_to_deleted(id)
            elif existing_setting['type'] == 'google-drive':
                move_google_drive_report_to_deleted(id)
        except Exception as e:
            # Log the error but don't fail the request
            logger.error(f"Error moving report folder for setting {id}: {str(e)}")

        # Return 204 No Content
        return None