import os
import sys

# Add the parent directory of src to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import argparse
from src.session import get_session
from src.generating_reports.systems.filesystem import save_filesystem_report_and_send_messages
from src.generating_reports.systems.yandex_disk import save_yandex_disk_report_and_send_messages
from src.generating_reports.systems.google_drive import save_google_drive_report_and_send_messages
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "save_report.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("save_report")

def save_report(setting_id: int):
    """
    Generate and save a report for the given setting ID
    
    Args:
        setting_id: The ID of the setting to generate a report for
    """
    try:
        logger.info(f"Starting report generation for setting ID: {setting_id}")
        
        # Get setting information from database
        with get_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM settings WHERE setting_id = ?", (setting_id,))
            setting = cursor.fetchone()

            if not setting:
                logger.error(f"Setting with ID {setting_id} not found")
                return

            # Log the setting info for debugging
            logger.info(f"Found setting: {setting['setting_name']}")

            if setting['type'] == 'filesystem':
                save_filesystem_report_and_send_messages(setting)

            if setting['type'] == 'yandex-disk':
                save_yandex_disk_report_and_send_messages(setting)

            if setting['type'] == 'google-drive':
                save_google_drive_report_and_send_messages(setting)

            logger.info(f"Report for setting ID {setting_id} has been processed")
            
    except Exception as e:
        logger.error(f"Error generating report for setting ID {setting_id}: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a report for a specific setting")
    parser.add_argument("setting_id", type=int, help="The ID of the setting to generate a report for")
    
    args = parser.parse_args()
    save_report(args.setting_id)