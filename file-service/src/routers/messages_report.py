from fastapi import APIRouter, Query, HTTPException
from src.schemas.endpoints.message_report import MessageReportGet
from src.session import get_session
import json

message_report_router = APIRouter(tags=["messages_report"])


@message_report_router.get(
    "/setting/{setting_id}/report/{report_id}/messages_report", 
    response_model=list[MessageReportGet], 
    description="Get all messages that are associated with a provided report", 
    responses={404:{
        "description": "Report not found"
    }}
)
async def get_messages_from_report(
    setting_id: int,
    report_id: int,
    offset: int = Query(default=0, description="The offset of the messages"), 
    limit: int = Query(default=10, description="The limit of the messages"),
    user_ids: list[str] = Query(default=None, description="The list of user ids to filter by")
):
    with get_session() as conn:
        cursor = conn.cursor()
        
        # Check if report exists
        cursor.execute(
            "SELECT * FROM reports WHERE setting_id = ? AND report_id = ?", 
            (setting_id, report_id)
        )
        report = cursor.fetchone()
        if not report:
            raise HTTPException(status_code=404, detail=f"Report not found for setting ID {setting_id} and report ID {report_id}")
        
        # Build query
        query = "SELECT * FROM messages_reports WHERE setting_id = ? AND report_id = ?"
        params = [setting_id, report_id]
        
        # Add filter by user IDs if provided
        if user_ids:
            placeholders = ','.join(['?'] * len(user_ids))
            query += f" AND sender_id IN ({placeholders})"
            params.extend(user_ids)
        
        # Add pagination
        query += " ORDER BY timedata DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute query
        cursor.execute(query, params)
        messages = cursor.fetchall()
        
        # Convert to schemas
        return [
            MessageReportGet(
                message_id=message["message_id"],
                sender_phone_number=message["sender_phone_number"],
                sender_name=message["sender_name"],
                sender_id=message["sender_id"],
                setting_id=message["setting_id"],
                report_id=message["report_id"],
                original_message_text=message["original_message_text"],
                formatted_message_text=json.loads(message["formatted_message_text"]) if isinstance(message["formatted_message_text"], str) else message["formatted_message_text"],
                timedata=message["timedata"],
                images=json.loads(message["images"]) if message["images"] else {"images": []},
                extra=json.loads(message["extra"]) if message["extra"] and isinstance(message["extra"], str) else (message["extra"] or {})
            )
            for message in messages
        ]


# @message_report_router.get(
#     "/setting/{setting_id}/report/{report_id}/message_report/{message_report_id}",
#     response_model=MessageReportGet,
#     description="Get a message from a report by its id",
#     responses={404:{
#         "description": "Report or message not found"
#     }}
# )
# async def get_message_from_report(
#     setting_id: int,
#     report_id: int,
#     message_report_id: int
# ):
#     pass