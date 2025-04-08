import uvicorn
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from datetime import datetime, timedelta

MOCK_API_PORT = 3000  # Default DATA_SERVICE_PORT used in the presentation service main.py

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MockDataService")

app = FastAPI(
    title="Mock Data Service",
    description="Simulates the data service API for testing the presentation service.",
    version="0.2.0"
)

def generate_timestamp(days_offset=0, hour=12, minute=0, second=0, base_date=datetime(2024, 7, 15)):
    """Generates an ISO 8601 formatted timestamp string with a Z timezone indicator."""
    dt = base_date + timedelta(days=days_offset, hours=hour - base_date.hour, minutes=minute - base_date.minute, seconds=second - base_date.second)
    return dt.isoformat() + "Z"

MOCK_MESSAGES_DB: Dict[str, List[Dict[str, Any]]] = {

    # Chat 1: Field Reports (Focus on Incidents and Observations)
    "field_reports_1": [
        {
            "_id": "fr1_001", "message_id": "101", "source_name": "telegram", "chat_id": "field_reports_1",
            "text": "Field 777, major locust swarm observed moving east.",
            "sender_id": "agro_1", "sender_name": "John Doe", "image": None,
            "data": {"message_type": "инцидент", "field": "777", "incident": "locust swarm", "severity": "high", "direction": "east"},
            "timestamp": generate_timestamp(days_offset=0, hour=9, minute=15), "updated_at": generate_timestamp(days_offset=0, hour=9, minute=16)
        },
        {
            "_id": "fr1_002", "message_id": "102", "source_name": "telegram", "chat_id": "field_reports_1",
            "text": "Field 42, signs of fungal infection on lower leaves, approx 10% affected.",
            "sender_id": "agro_2", "sender_name": "Jane Smith", "image": None,
            "data": {"message_type": "инцидент", "field": "42", "incident": "fungal infection signs", "affected_area_percent": 10, "location_detail": "lower leaves"},
            "timestamp": generate_timestamp(days_offset=0, hour=14, minute=30), "updated_at": generate_timestamp(days_offset=0, hour=14, minute=31)
        },
        {
            "_id": "fr1_003", "message_id": "103", "source_name": "whatsapp", "chat_id": "field_reports_1",
            "text": "Irrigation system leak detected near pump station B on Field 777.",
            "sender_id": "tech_1", "sender_name": "Mike Ross", "image": None,
            "data": {"message_type": "инцидент", "field": "777", "incident": "irrigation leak", "component": "Pump Station B"},
            "timestamp": generate_timestamp(days_offset=1, hour=8, minute=0), "updated_at": generate_timestamp(days_offset=1, hour=8, minute=1)
        },
        {
            "_id": "fr1_004", "message_id": "104", "source_name": "telegram", "chat_id": "field_reports_1",
            "text": "Field 101 looks healthy, good growth observed.",
            "sender_id": "agro_1", "sender_name": "John Doe", "image": None,
            "data": {"message_type": "наблюдение", "field": "101", "observation": "healthy growth"},
            "timestamp": generate_timestamp(days_offset=1, hour=11, minute=45), "updated_at": generate_timestamp(days_offset=1, hour=11, minute=46)
        },
         {
            "_id": "fr1_005", "message_id": "105", "source_name": "telegram", "chat_id": "field_reports_1",
            "text": "Weeds growing rapidly in section C of Field 42. Needs attention.",
            "sender_id": "agro_2", "sender_name": "Jane Smith", "image": None,
            "data": {"message_type": "инцидент", "field": "42", "incident": "rapid weed growth", "location_detail": "section C", "severity": "medium"},
            "timestamp": generate_timestamp(days_offset=2, hour=10, minute=0), "updated_at": generate_timestamp(days_offset=2, hour=10, minute=1)
        },
        { # Older message, potentially outside typical time filter
            "_id": "fr1_006", "message_id": "98", "source_name": "telegram", "chat_id": "field_reports_1",
            "text": "Minor frost damage on Field 55 from last week.",
            "sender_id": "agro_1", "sender_name": "John Doe", "image": None,
            "data": {"message_type": "инцидент", "field": "55", "incident": "frost damage", "severity": "low"},
            "timestamp": generate_timestamp(days_offset=-7, hour=7, minute=0), "updated_at": generate_timestamp(days_offset=-7, hour=7, minute=1)
        },
    ],

    # Chat 2: Machinery Logs (Focus on Tasks, Status, Maintenance)
    "machinery_log_alpha": [
        {
            "_id": "ml_a_001", "message_id": "201", "source_name": "whatsapp", "chat_id": "machinery_log_alpha",
            "text": "Task: Plow Field 123 today. Assigned to Tractor T-150 (Driver: Bob).",
            "sender_id": "mgr_1", "sender_name": "Alice Green", "image": None,
            "data": {"message_type": "задача", "field": "123", "task": "plowing", "vehicle": "Tractor T-150", "assigned_to": "Bob"},
            "timestamp": generate_timestamp(days_offset=0, hour=7, minute=0), "updated_at": generate_timestamp(days_offset=0, hour=7, minute=1)
        },
        {
            "_id": "ml_a_002", "message_id": "202", "source_name": "whatsapp", "chat_id": "machinery_log_alpha",
            "text": "T-150 started plowing Field 123 at 08:30.",
            "sender_id": "driver_bob", "sender_name": "Bob White", "image": None,
            "data": {"message_type": "статус", "field": "123", "vehicle": "Tractor T-150", "status": "started plowing", "start_time": "08:30"},
            "timestamp": generate_timestamp(days_offset=0, hour=8, minute=35), "updated_at": generate_timestamp(days_offset=0, hour=8, minute=36)
        },
        {
            "_id": "ml_a_003", "message_id": "203", "source_name": "whatsapp", "chat_id": "machinery_log_alpha",
            "text": "Task completed: Field 123 plowing finished. Duration: 4 hours. Fuel used: 80 liters.",
            "sender_id": "driver_bob", "sender_name": "Bob White", "image": None,
            "data": {"message_type": "отчет", "field": "123", "task": "plowing", "status": "completed", "vehicle": "Tractor T-150", "duration_hours": 4, "fuel_liters": 80},
            "timestamp": generate_timestamp(days_offset=0, hour=12, minute=40), "updated_at": generate_timestamp(days_offset=0, hour=12, minute=41)
        },
        {
            "_id": "ml_a_004", "message_id": "204", "source_name": "telegram", "chat_id": "machinery_log_alpha",
            "text": "Harvester H-1 needs maintenance. Low hydraulic pressure warning.",
            "sender_id": "driver_carol", "sender_name": "Carol Black", "image": None,
            "data": {"message_type": "инцидент", "vehicle": "Harvester H-1", "incident": "maintenance needed", "details": "low hydraulic pressure warning", "urgency": "medium"},
            "timestamp": generate_timestamp(days_offset=1, hour=15, minute=0), "updated_at": generate_timestamp(days_offset=1, hour=15, minute=1)
        },
        {
            "_id": "ml_a_005", "message_id": "205", "source_name": "telegram", "chat_id": "machinery_log_alpha",
            "text": "Maintenance scheduled for H-1 tomorrow morning.",
            "sender_id": "mgr_1", "sender_name": "Alice Green", "image": None,
            "data": {"message_type": "уведомление", "vehicle": "Harvester H-1", "event": "maintenance scheduled", "scheduled_time": "tomorrow morning"},
            "timestamp": generate_timestamp(days_offset=1, hour=16, minute=30), "updated_at": generate_timestamp(days_offset=1, hour=16, minute=31)
        },
         {
            "_id": "ml_a_006", "message_id": "206", "source_name": "whatsapp", "chat_id": "machinery_log_alpha",
            "text": "Requesting fuel delivery for Tractor T-150 at Field 200.",
            "sender_id": "driver_bob", "sender_name": "Bob White", "image": None,
            "data": {"message_type": "запрос", "request_type": "fuel delivery", "vehicle": "Tractor T-150", "location": "Field 200"},
            "timestamp": generate_timestamp(days_offset=2, hour=9, minute=0), "updated_at": generate_timestamp(days_offset=2, hour=9, minute=1)
        },
    ],

    # Chat 3: Irrigation Control (Focus on Status, Measurements, Alerts)
    "irrigation_control_west": [
        {
            "_id": "icw_001", "message_id": "301", "source_name": "system_api", "chat_id": "irrigation_control_west",
            "text": "Sensor W-05 (Field 300) reports soil moisture: 55%",
            "sender_id": "sensor_w05", "sender_name": "Sensor W-05", "image": None,
            "data": {"message_type": "отчет", "field": "300", "sensor_id": "W-05", "measurement": "soil moisture", "value_percent": 55, "units": "%"},
            "timestamp": generate_timestamp(days_offset=0, hour=6, minute=0), "updated_at": generate_timestamp(days_offset=0, hour=6, minute=0)
        },
        {
            "_id": "icw_002", "message_id": "302", "source_name": "system_api", "chat_id": "irrigation_control_west",
            "text": "Sensor W-12 (Field 310) reports soil moisture: 38% - Below threshold!",
            "sender_id": "sensor_w12", "sender_name": "Sensor W-12", "image": None,
            "data": {"message_type": "оповещение", "field": "310", "sensor_id": "W-12", "alert_type": "low moisture", "value_percent": 38, "threshold_percent": 40},
            "timestamp": generate_timestamp(days_offset=0, hour=6, minute=5), "updated_at": generate_timestamp(days_offset=0, hour=6, minute=5)
        },
        {
            "_id": "icw_003", "message_id": "303", "source_name": "telegram", "chat_id": "irrigation_control_west",
            "text": "Activating irrigation cycle for Field 310 for 60 minutes due to low moisture.",
            "sender_id": "irrigation_mgr", "sender_name": "David Lee", "image": None,
            "data": {"message_type": "действие", "field": "310", "action": "activate irrigation", "duration_minutes": 60, "reason": "low moisture alert"},
            "timestamp": generate_timestamp(days_offset=0, hour=6, minute=15), "updated_at": generate_timestamp(days_offset=0, hour=6, minute=16)
        },
        {
            "_id": "icw_004", "message_id": "304", "source_name": "system_api", "chat_id": "irrigation_control_west",
            "text": "Irrigation cycle completed for Field 310.",
            "sender_id": "irrigation_ctrl", "sender_name": "Control System", "image": None,
            "data": {"message_type": "статус", "field": "310", "event": "irrigation cycle completed"},
            "timestamp": generate_timestamp(days_offset=0, hour=7, minute=15), "updated_at": generate_timestamp(days_offset=0, hour=7, minute=15)
        },
        {
            "_id": "icw_005", "message_id": "305", "source_name": "system_api", "chat_id": "irrigation_control_west",
            "text": "Sensor W-12 (Field 310) reports soil moisture: 62%",
            "sender_id": "sensor_w12", "sender_name": "Sensor W-12", "image": None,
            "data": {"message_type": "отчет", "field": "310", "sensor_id": "W-12", "measurement": "soil moisture", "value_percent": 62, "units": "%"},
            "timestamp": generate_timestamp(days_offset=0, hour=8, minute=0), "updated_at": generate_timestamp(days_offset=0, hour=8, minute=0)
        },
    ],

    # Chat 4: Pest Alerts (Focus on Alerts, Confirmations, Actions)
    "pest_alerts_central": [
        {
            "_id": "pac_001", "message_id": "401", "source_name": "telegram", "chat_id": "pest_alerts_central",
            "text": "High activity of aphids detected in trap C-5 (Field 500).",
            "sender_id": "scout_1", "sender_name": "Eva Adams", "image": None,
            "data": {"message_type": "оповещение", "field": "500", "pest": "aphids", "detection_method": "trap C-5", "level": "high"},
            "timestamp": generate_timestamp(days_offset=1, hour=10, minute=0), "updated_at": generate_timestamp(days_offset=1, hour=10, minute=1)
        },
        {
            "_id": "pac_002", "message_id": "402", "source_name": "telegram", "chat_id": "pest_alerts_central",
            "text": "Confirming aphid presence in Field 500. Recommend spraying.",
            "sender_id": "agronomist_lead", "sender_name": "Frank Harris", "image": None,
            "data": {"message_type": "подтверждение", "field": "500", "pest": "aphids", "confirmation": True, "recommendation": "spraying"},
            "timestamp": generate_timestamp(days_offset=1, hour=11, minute=30), "updated_at": generate_timestamp(days_offset=1, hour=11, minute=31)
        },
        {
            "_id": "pac_003", "message_id": "403", "source_name": "telegram", "chat_id": "pest_alerts_central",
            "text": "Action: Scheduled spraying for Field 500 tomorrow AM.",
            "sender_id": "agronomist_lead", "sender_name": "Frank Harris", "image": None,
            "data": {"message_type": "действие", "field": "500", "action": "schedule spraying", "pest": "aphids", "timing": "tomorrow AM"},
            "timestamp": generate_timestamp(days_offset=1, hour=14, minute=0), "updated_at": generate_timestamp(days_offset=1, hour=14, minute=1)
        },
        {
            "_id": "pac_004", "message_id": "404", "source_name": "telegram", "chat_id": "pest_alerts_central",
            "text": "Low activity of spider mites in trap C-8 (Field 510). Monitoring.",
            "sender_id": "scout_2", "sender_name": "George Clark", "image": None,
            "data": {"message_type": "наблюдение", "field": "510", "pest": "spider mites", "detection_method": "trap C-8", "level": "low", "action": "monitoring"},
            "timestamp": generate_timestamp(days_offset=2, hour=9, minute=30), "updated_at": generate_timestamp(days_offset=2, hour=9, minute=31)
        },
    ],

    # Chat 5: Agronomist Tasks (Focus on Task assignment, progress, questions)
    "agronomist_tasks_beta": [
        {
            "_id": "atb_001", "message_id": "501", "source_name": "whatsapp", "chat_id": "agronomist_tasks_beta",
            "text": "Assigning soil sampling task for Fields 600-605 to @JaneSmith.",
            "sender_id": "lead_agro", "sender_name": "Hannah Davis", "image": None,
            "data": {"message_type": "задача", "fields": ["600", "601", "602", "603", "604", "605"], "task": "soil sampling", "assigned_to": "Jane Smith"},
            "timestamp": generate_timestamp(days_offset=0, hour=9, minute=0), "updated_at": generate_timestamp(days_offset=0, hour=9, minute=1)
        },
        {
            "_id": "atb_002", "message_id": "502", "source_name": "whatsapp", "chat_id": "agronomist_tasks_beta",
            "text": "Started soil sampling in Field 600.",
            "sender_id": "agro_2", "sender_name": "Jane Smith", "image": None,
            "data": {"message_type": "статус", "field": "600", "task": "soil sampling", "status": "started"},
            "timestamp": generate_timestamp(days_offset=0, hour=10, minute=30), "updated_at": generate_timestamp(days_offset=0, hour=10, minute=31)
        },
        {
            "_id": "atb_003", "message_id": "503", "source_name": "whatsapp", "chat_id": "agronomist_tasks_beta",
            "text": "Question: What depth should the samples be taken from in Field 603? Standard 15cm or deeper?",
            "sender_id": "agro_2", "sender_name": "Jane Smith", "image": None,
            "data": {"message_type": "вопрос", "field": "603", "task": "soil sampling", "question": "sample depth", "options": ["15cm", "deeper"]},
            "timestamp": generate_timestamp(days_offset=1, hour=11, minute=0), "updated_at": generate_timestamp(days_offset=1, hour=11, minute=1)
        },
        {
            "_id": "atb_004", "message_id": "504", "source_name": "whatsapp", "chat_id": "agronomist_tasks_beta",
            "text": "@JaneSmith Use standard 15cm for Field 603.",
            "sender_id": "lead_agro", "sender_name": "Hannah Davis", "image": None,
            "data": {"message_type": "ответ", "field": "603", "question_ref": "sample depth", "answer": "15cm"},
            "timestamp": generate_timestamp(days_offset=1, hour=11, minute=15), "updated_at": generate_timestamp(days_offset=1, hour=11, minute=16)
        },
        {
            "_id": "atb_005", "message_id": "505", "source_name": "whatsapp", "chat_id": "agronomist_tasks_beta",
            "text": "Soil sampling completed for Fields 600-605. Samples sent to lab.",
            "sender_id": "agro_2", "sender_name": "Jane Smith", "image": None,
            "data": {"message_type": "отчет", "fields": ["600", "601", "602", "603", "604", "605"], "task": "soil sampling", "status": "completed", "next_step": "sent to lab"},
            "timestamp": generate_timestamp(days_offset=2, hour=16, minute=0), "updated_at": generate_timestamp(days_offset=2, hour=16, minute=1)
        },
    ],

    # Chat 6: Soil Lab Results (Focus on Reports with numerical data)
    "soil_lab_results": [
        {
            "_id": "slr_001", "message_id": "601", "source_name": "lab_system", "chat_id": "soil_lab_results",
            "text": "Results for Field 600 (Sample ID: S600-01): pH: 6.8, Nitrogen (N): 15 ppm, Phosphorus (P): 25 ppm, Potassium (K): 120 ppm",
            "sender_id": "lab_tech_1", "sender_name": "Lab System Alpha", "image": None,
            "data": {"message_type": "отчет", "report_type": "soil analysis", "field": "600", "sample_id": "S600-01", "ph": 6.8, "nitrogen_ppm": 15, "phosphorus_ppm": 25, "potassium_ppm": 120},
            "timestamp": generate_timestamp(days_offset=3, hour=10, minute=0), "updated_at": generate_timestamp(days_offset=3, hour=10, minute=0)
        },
        {
            "_id": "slr_002", "message_id": "602", "source_name": "lab_system", "chat_id": "soil_lab_results",
            "text": "Results for Field 601 (Sample ID: S601-01): pH: 7.1, N: 12 ppm, P: 30 ppm, K: 110 ppm",
            "sender_id": "lab_tech_1", "sender_name": "Lab System Alpha", "image": None,
            "data": {"message_type": "отчет", "report_type": "soil analysis", "field": "601", "sample_id": "S601-01", "ph": 7.1, "nitrogen_ppm": 12, "phosphorus_ppm": 30, "potassium_ppm": 110},
            "timestamp": generate_timestamp(days_offset=3, hour=10, minute=5), "updated_at": generate_timestamp(days_offset=3, hour=10, minute=5)
        },
        {
            "_id": "slr_003", "message_id": "603", "source_name": "lab_system", "chat_id": "soil_lab_results",
            "text": "Results for Field 602 (Sample ID: S602-01): pH: 6.5, N: 18 ppm, P: 22 ppm, K: 135 ppm, Organic Matter: 3.5%",
            "sender_id": "lab_tech_1", "sender_name": "Lab System Alpha", "image": None,
            "data": {"message_type": "отчет", "report_type": "soil analysis", "field": "602", "sample_id": "S602-01", "ph": 6.5, "nitrogen_ppm": 18, "phosphorus_ppm": 22, "potassium_ppm": 135, "organic_matter_percent": 3.5},
            "timestamp": generate_timestamp(days_offset=3, hour=10, minute=10), "updated_at": generate_timestamp(days_offset=3, hour=10, minute=10)
        },
        # Add more results for fields 603, 604, 605 similarly
    ],

    # Chat 7: Empty Chat (To test handling of no messages)
    "empty_chat": [],

    # Chat 8: Mixed Content (Various message types for complex mapping tests)
    "mixed_content_chat": [
         {
            "_id": "mcc_001", "message_id": "801", "source_name": "telegram", "chat_id": "mixed_content_chat",
            "text": "Reminder: Team meeting today at 14:00.",
            "sender_id": "admin_bot", "sender_name": "Admin Bot", "image": None,
            "data": {"message_type": "уведомление", "event": "team meeting", "time": "14:00 today"},
            "timestamp": generate_timestamp(days_offset=0, hour=9, minute=0), "updated_at": generate_timestamp(days_offset=0, hour=9, minute=1)
        },
        {
            "_id": "mcc_002", "message_id": "802", "source_name": "whatsapp", "chat_id": "mixed_content_chat",
            "text": "Need someone to check the fence line on Field 900 south border.",
            "sender_id": "mgr_2", "sender_name": "Olivia Brown", "image": None,
            "data": {"message_type": "запрос", "request_type": "check fence", "field": "900", "location_detail": "south border"},
            "timestamp": generate_timestamp(days_offset=0, hour=11, minute=0), "updated_at": generate_timestamp(days_offset=0, hour=11, minute=1)
        },
        {
            "_id": "mcc_003", "message_id": "803", "source_name": "telegram", "chat_id": "mixed_content_chat",
            "text": "Checked fence on Field 900 south, looks secure.",
            "sender_id": "worker_1", "sender_name": "Peter Jones", "image": None,
            "data": {"message_type": "отчет", "task": "check fence", "field": "900", "location_detail": "south border", "status": "secure"},
            "timestamp": generate_timestamp(days_offset=0, hour=15, minute=30), "updated_at": generate_timestamp(days_offset=0, hour=15, minute=31)
        },
        {
            "_id": "mcc_004", "message_id": "804", "source_name": "telegram", "chat_id": "mixed_content_chat",
            "text": "Weather update: Chance of rain increasing this afternoon.",
            "sender_id": "weather_svc", "sender_name": "Weather Service", "image": None,
            "data": {"message_type": "оповещение", "alert_type": "weather update", "condition": "increasing chance of rain", "timing": "this afternoon"},
            "timestamp": generate_timestamp(days_offset=1, hour=10, minute=0), "updated_at": generate_timestamp(days_offset=1, hour=10, minute=0)
        },
         { # Message with cost data for SUM aggregation testing
            "_id": "mcc_005", "message_id": "805", "source_name": "whatsapp", "chat_id": "mixed_content_chat",
            "text": "Purchased 5 bags of fertilizer for Field 900. Cost: 250 EUR.",
            "sender_id": "mgr_2", "sender_name": "Olivia Brown", "image": None,
            "data": {"message_type": "закупка", "item": "fertilizer", "quantity": 5, "unit": "bags", "field": "900", "cost": 250.00, "currency": "EUR"},
            "timestamp": generate_timestamp(days_offset=1, hour=12, minute=0), "updated_at": generate_timestamp(days_offset=1, hour=12, minute=1)
        },
         { # Another purchase for the same field
            "_id": "mcc_006", "message_id": "806", "source_name": "whatsapp", "chat_id": "mixed_content_chat",
            "text": "Bought new set of plow blades. Cost 125.50 EUR.",
            "sender_id": "mgr_2", "sender_name": "Olivia Brown", "image": None,
            "data": {"message_type": "закупка", "item": "plow blades", "quantity": 1, "unit": "set", "cost": 125.50, "currency": "EUR"},
            "timestamp": generate_timestamp(days_offset=2, hour=13, minute=0), "updated_at": generate_timestamp(days_offset=2, hour=13, minute=1)
        },
    ]
}

# --- API Endpoint ---
@app.get(
    "/api/chats/messages/{chat_id}",
    summary="Get Processed Messages for a Chat",
    description="Returns a predefined list of processed messages for known chat_ids, "
                "or an empty list for unknown ones. Simulates the real data service endpoint.",
    response_model=List[Dict[str, Any]]
)
async def get_chat_messages(chat_id: str):
    """
    Handles requests to fetch messages for a specific chat ID.
    Retrieves data from the MOCK_MESSAGES_DB.
    """
    logger.info(f"Received request for chat_id: {chat_id}")

    # Retrieve messages for the given chat_id. Return empty list if not found.
    messages = MOCK_MESSAGES_DB.get(chat_id, [])

    if messages:
        logger.info(f"Found data for chat_id '{chat_id}'. Returning {len(messages)} messages.")
    elif chat_id in MOCK_MESSAGES_DB: # Handles the case where the chat exists but is empty
         logger.info(f"Chat_id '{chat_id}' exists but is empty. Returning 0 messages.")
    else:
        logger.warning(f"chat_id '{chat_id}' not found in mock database. Returning empty list.")

    return JSONResponse(content=messages, status_code=200)

if __name__ == "__main__":
    logger.info(f"Starting Mock Data Service on port {MOCK_API_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=MOCK_API_PORT)

