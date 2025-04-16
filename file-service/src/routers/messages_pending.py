from fastapi import APIRouter, Query, HTTPException
from src.schemas.endpoints.message_pending import MessagePendingGet, MessagePendingPost, MessagePendingPut
from src.session import get_session
import json
from datetime import datetime, timezone
from src.auxiliary.testing import update_google_drive, update_yandex_disk

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
    with get_session() as conn:
        # Check if setting exists
        cursor = conn.cursor()
        cursor.execute("SELECT setting_id FROM settings WHERE setting_id = ?", (setting_id,))
        setting = cursor.fetchone()
        if not setting:
            raise HTTPException(status_code=404, detail="Setting not found")
        
        # Build query
        query = "SELECT * FROM messages_pending WHERE setting_id = ?"
        params = [setting_id]
        
        # Add filter by phone numbers if provided
        if user_phone_numbers:
            placeholders = ','.join(['?'] * len(user_phone_numbers))
            query += f" AND sender_phone_number IN ({placeholders})"
            params.extend(user_phone_numbers)
        
        # Add pagination
        query += " ORDER BY timedata DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute query
        cursor.execute(query, params)
        messages = cursor.fetchall()
        
        # Convert to schemas
        result = []
        for message in messages:
            # Parse JSON strings to dictionaries
            formatted_message_text = json.loads(message["formatted_message_text"]) if message["formatted_message_text"] else {}
            images = json.loads(message["images"]) if message["images"] else {"images": []}
            extra = json.loads(message["extra"]) if message["extra"] else {}
            
            result.append(
                MessagePendingGet(
                    message_id=message["message_id"],
                    sender_phone_number=message["sender_phone_number"],
                    sender_name=message["sender_name"],
                    sender_id=message["sender_id"],
                    setting_id=message["setting_id"],
                    original_message_text=message["original_message_text"],
                    formatted_message_text=formatted_message_text,
                    timedata=message["timedata"],
                    images=images,
                    extra=extra
                )
            )

        return result


@message_pending_router.post(
    "/setting/{setting_id}/message_pending", 
    response_model=MessagePendingGet, 
    description="Create a pending message for a setting", 
    responses={404:{
        "description": "Setting not found"
    }}
)
async def create_message(
    setting_id: int, 
    message: MessagePendingPost
):
    with get_session() as conn:
        cursor = conn.cursor()
        
        # Check if setting exists
        cursor.execute("SELECT setting_id, type FROM settings WHERE setting_id = ?", (setting_id,))
        setting = cursor.fetchone()
        if not setting:
            raise HTTPException(status_code=404, detail="Setting not found")
        
        setting_type = setting[1]
        
        # Insert the new message
        current_time = datetime.now(timezone.utc).isoformat()
        
        # Convert images to a serializable format if it's an object
        images_data = message.images
        if hasattr(images_data, "__dict__"):
            images_data = images_data.__dict__
        
        cursor.execute(
            """
            INSERT INTO messages_pending 
            (sender_phone_number, sender_name, sender_id, setting_id, 
             original_message_text, formatted_message_text, images, timedata, extra) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.sender_phone_number,
                message.sender_name,
                message.sender_id,
                setting_id,
                message.original_message_text,
                json.dumps(message.formatted_message_text),
                json.dumps(images_data),
                current_time,
                json.dumps(message.extra)
            )
        )
        
        # Get the ID of the newly inserted message
        message_id = cursor.lastrowid

        testing = message.extra.get("testing", False)
        if testing:
            if setting_type == "google-drive":
                await update_google_drive(message, setting_id, conn)
            elif setting_type == "yandex-disk":
                await update_yandex_disk(message, setting_id, conn)
        
        # Return the created message
        return MessagePendingGet(
            message_id=message_id,
            sender_phone_number=message.sender_phone_number,
            sender_name=message.sender_name,
            sender_id=message.sender_id,
            setting_id=setting_id,
            original_message_text=message.original_message_text,
            formatted_message_text=message.formatted_message_text,
            images=message.images,
            timedata=current_time,
            extra=message.extra
        )


@message_pending_router.put(
    "/setting/{setting_id}/message_pending/{message_id}", 
    response_model=MessagePendingGet, 
    description="Update a pending message by its id", 
    responses={404:{
        "description": "Setting or message not found"
    }}
)
async def update_message(
    setting_id: int, 
    message_id: int,
    message_put: MessagePendingPut
):
    with get_session() as conn:
        cursor = conn.cursor()
        
        # Check if message exists
        cursor.execute(
            "SELECT * FROM messages_pending WHERE setting_id = ? AND message_id = ?", 
            (setting_id, message_id)
        )
        message = cursor.fetchone()
        
        if not message:
            raise HTTPException(status_code=404, detail=f"Message not found for setting ID {setting_id} and message ID {message_id}")
        
        # Convert JSON fields to string
        formatted_message_text_json = json.dumps(message_put.formatted_message_text)
        extra_json = json.dumps(message_put.extra)
        
        # Convert images to a serializable format if it's an object
        images_data = message_put.images
        if hasattr(images_data, "__dict__"):
            images_data = images_data.__dict__
        
        # Build the update query
        query = """
        UPDATE messages_pending SET
            original_message_text = ?,
            formatted_message_text = ?,
            images = ?,
            extra = ?
        WHERE setting_id = ? AND message_id = ?
        """
        
        # Execute the update
        cursor.execute(query, (
            message_put.original_message_text,
            formatted_message_text_json,
            json.dumps(images_data),
            extra_json,
            setting_id,
            message_id
        ))
        
        # Check if the update was successful
        if cursor.rowcount == 0:
            raise HTTPException(status_code=500, detail="Failed to update message")
        
        # Get the updated message
        cursor.execute(
            "SELECT * FROM messages_pending WHERE setting_id = ? AND message_id = ?", 
            (setting_id, message_id)
        )
        updated_message = cursor.fetchone()
        
        # Parse JSON strings to dictionaries
        formatted_message_text = json.loads(updated_message["formatted_message_text"]) if updated_message["formatted_message_text"] else {}
        images = json.loads(updated_message["images"]) if updated_message["images"] else {"images": []}
        extra = json.loads(updated_message["extra"]) if updated_message["extra"] else {}
        
        # Return the updated message
        return MessagePendingGet(
            message_id=updated_message["message_id"],
            sender_phone_number=updated_message["sender_phone_number"],
            sender_name=updated_message["sender_name"],
            sender_id=updated_message["sender_id"],
            setting_id=updated_message["setting_id"],
            original_message_text=updated_message["original_message_text"],
            formatted_message_text=formatted_message_text,
            images=images,
            timedata=updated_message["timedata"],
            extra=extra
        )


@message_pending_router.delete(
    "/setting/{setting_id}/message_pending/{message_id}",
    response_model=None,
    status_code=204,
    description="Delete a pending message by its id",
    responses={404:{
        "description": "Setting or message not found"
    }}
)
async def delete_message(
    setting_id: int,
    message_id: int
):
    with get_session() as conn:
        cursor = conn.cursor()
        
        # Check if message exists
        cursor.execute(
            "SELECT message_id FROM messages_pending WHERE setting_id = ? AND message_id = ?", 
            (setting_id, message_id)
        )
        message = cursor.fetchone()
        
        if not message:
            raise HTTPException(status_code=404, detail=f"Message not found for setting ID {setting_id} and message ID {message_id}")
        
        # Delete the message
        cursor.execute(
            "DELETE FROM messages_pending WHERE setting_id = ? AND message_id = ?", 
            (setting_id, message_id)
        )
        
        # Check if the deletion was successful
        if cursor.rowcount == 0:
            raise HTTPException(status_code=500, detail="Failed to delete message")
        
        # Return 204 No Content
        return None