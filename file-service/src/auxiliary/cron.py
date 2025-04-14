import os
import sys
from crontab import CronTab
from src.schemas.endpoints.setting import SettingPost
from src.config import logger

# Path to the cron configuration directory
CRON_CONFIG_DIR = "/var/spool/cron/crontabs"

def create_cron_job(setting_id: int, setting: SettingPost):
    try:
        # Create the cron directory if it doesn't exist
        os.makedirs(CRON_CONFIG_DIR, exist_ok=True)
        
        # Use the current user's crontab
        cron = CronTab(user=True)
        # Get absolute path to the save_report.py script
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        save_report_path = os.path.join(script_dir, "save_report.py")
        python_path = sys.executable
        
        # Create the job
        job = cron.new(
            command=f"{python_path} {save_report_path} {setting_id} > /proc/1/fd/1 2>/proc/1/fd/2"
        )
        
        # Set the schedule from the setting
        job.setall(
            setting.minute,
            setting.hour,
            setting.day_of_month,
            setting.month,
            setting.day_of_week
        )
        
        # Write the crontab
        cron.write()
        logger.info(f"Created cron job for setting ID {setting_id}")
        return True
    except Exception as e:
        logger.error(f"Error creating cron job: {str(e)}")
        raise

def delete_cron_job(setting_id: int):
    """
    Delete a cron job for a specific setting ID
    
    Args:
        setting_id: The ID of the setting whose cron job should be deleted
    
    Returns:
        bool: True if a job was found and deleted, False otherwise
    """
    try:
        cron = CronTab(user=True)
        
        # Get absolute path to the save_report.py script
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        save_report_path = os.path.join(script_dir, "save_report.py")
        
        # Find jobs that match our pattern
        job_found = False
        for job in cron.find_command(f"{save_report_path} {setting_id}"):
            cron.remove(job)
            job_found = True
        
        # Also check without the full path, in case it was created differently
        for job in cron.find_command(f"save_report.py {setting_id}"):
            cron.remove(job)
            job_found = True
        
        # Write the changes to the crontab
        if job_found:
            cron.write()
            logger.info(f"Deleted cron job for setting ID {setting_id}")
        
        return job_found
    except Exception as e:
        logger.error(f"Error deleting cron job: {str(e)}")
        raise