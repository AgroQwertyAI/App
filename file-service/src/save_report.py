import os
import sys
import asyncio
# Add the parent directory of src to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import argparse
import json
from src.newsletter import send_report
from src.session import get_session
from src.generating_reports.systems.filesystem import save_filesystem_report
from src.generating_reports.systems.yandex_disk import save_yandex_disk_report
from src.generating_reports.systems.google_drive import save_google_drive_report
from src.auxiliary.logging import log_info

async def save_report(setting_id: int):
    """
    Generate and save a report for the given setting ID
    
    Args:
        setting_id: The ID of the setting to generate a report for
    """
    try:
        log_info(f"Starting report generation for setting ID: {setting_id}", 'info')
        
        # Get setting information from database
        with get_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM settings WHERE setting_id = ?", (setting_id,))
            setting = cursor.fetchone()

            if not setting:
                log_info(f"Setting with ID {setting_id} not found", 'error')
                return

            # Log the setting info for debugging
            log_info(f"Found setting: {setting['setting_name']}", 'info')

        if setting['type'] == 'filesystem':
            file = await save_filesystem_report(setting)

        if setting['type'] == 'yandex-disk':
            file = await save_yandex_disk_report(setting)

        if setting['type'] == 'google-drive':
            file = await save_google_drive_report(setting)

        # Send report to specified contacts
        for message in json.loads(setting['send_to']) if isinstance(setting['send_to'], str) else setting['send_to']:
            send_report(file, message['messenger'], message['phone_number'])
        
        log_info(f"Report for setting ID {setting_id} has been processed", 'info')  
    except Exception as e:
        log_info(f"Error generating report for setting ID {setting_id}: {e}", 'error')
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a report for a specific setting")
    parser.add_argument("setting_id", type=int, help="The ID of the setting to generate a report for")
    
    args = parser.parse_args()
    asyncio.run(save_report(args.setting_id))