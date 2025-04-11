from fastapi import APIRouter, Query
from src.schemas.message_report import MessageReportGet

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
    user_phone_numbers: list[str] = Query(default=None, description="The list of user phone numbers to filter by")
):
    pass

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