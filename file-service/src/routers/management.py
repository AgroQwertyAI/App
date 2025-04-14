from fastapi import APIRouter, HTTPException
from src.session import get_session
from src.save_report import save_report

management_router = APIRouter(tags=["management"])

@management_router.post(
    "/settings/{setting_id}/generate", 
    status_code=200,
    response_model=None,
    description="Generate a report for a setting right now. This does NOT skip nearest cron job.",
    responses={404: {"description": "Setting not found"}}
)
async def generate_setting(
    setting_id: int
):
    # Check if the setting exists in the database
    with get_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM settings WHERE setting_id = ?", (setting_id,))
        setting = cursor.fetchone()
        
        if not setting:
            raise HTTPException(status_code=404, detail=f"Setting with ID {setting_id} not found")
    
    # Call the save_report function with the setting ID
    save_report(setting_id)
    
    return None