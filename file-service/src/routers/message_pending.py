from fastapi import APIRouter, Query
from src.schemas.message_pending import MessagePendingGet, MessagePendingPost, MessagePendingPatch

message_pending_router = APIRouter(tags=["messages_pending"])


@message_pending_router.get(
    "/setting/{setting_id}/messages_pending", 
    response_model=list[MessagePendingGet], 
    description="Get all pending messages for a setting", 
    responses={404:{
        "description": "Setting not found"
    }}
)
async def get_messages(
    setting_id: int,
    offset: int = Query(default=0, description="The offset of the messages"), 
    limit: int = Query(default=10, description="The limit of the messages"),
    user_phone_numbers: list[str] = Query(default=None, description="The list of user phone numbers to filter by")
):
    pass


@message_pending_router.post(
    "/setting/{setting_id}/message_pending", 
    response_model=MessagePendingGet, 
    description="Create a pending message for a setting", 
    responses={404:{
        "description": "Setting not found"
    }, 400: {
        'description': 'User with this phone number already posted a message'
    }}
)
async def create_message(
    setting_id: int, 
    message: MessagePendingPost
):
    pass


@message_pending_router.patch(
    "/setting/{setting_id}/message_pending", 
    response_model=MessagePendingGet, 
    description="Update a pending message by its id", 
    responses={404:{
        "description": "Setting or message not found"
    }}
)
async def update_message(
    setting_id: int, 
    message_patch: MessagePendingPatch,
    sender_id: str = Query(description="The id of the message sender")
):
    pass


@message_pending_router.delete(
    "/setting/{setting_id}/message_pending",
    response_model=None,
    description="Delete a pending message by its id",
    responses={404:{
        "description": "Setting or message not found"
    }}
)
async def delete_message(
    setting_id: int,
    sender_id: str = Query(description="The id of the message sender")
):
    pass