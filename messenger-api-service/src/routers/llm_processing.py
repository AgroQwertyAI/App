from fastapi import APIRouter
from sqlalchemy.orm import Session
from src.schemas.endpoints.llm_processing import LLMProcessingPayloadPost, LLMProcessingPayloadSend, Message, LLMProcessingPayloadSendResponse, LLMProcessingPayloadAnswer
from src.schemas.database import MessageHistory, LLMAnswer
from src.session import get_db
import httpx
from datetime import datetime
from dotenv import load_dotenv
from typing import List
from fastapi import HTTPException

load_dotenv()

LLM_PROCESSING_SERVICE_URL = "http://message-processing-service:52001"

llm_processing_router = APIRouter(tags=["LLM Processing"])

@llm_processing_router.post("/llm_processing",
    status_code=200,
    response_model=LLMProcessingPayloadAnswer | None,
    description="Process message received from telegram bot and send it to message processing service",
    responses={404: {"description": "No association found for chat_id"}}
)
async def llm_processing(payload: LLMProcessingPayloadPost):
    with get_db() as db:
        cursor = db.cursor()
        
        # Get setting_id from associations table
        cursor.execute(
            "SELECT setting_id FROM associations WHERE chat_id = ?",
            (payload.chat_id,)
        )
        result = cursor.fetchone()
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"No association found for chat_id {payload.chat_id}"
            )
        
        setting_id = result["setting_id"]
        
        # 1. Save the current message to message_history
        timestamp = datetime.now().isoformat()
        images_str = ",".join(payload.images) if payload.images else ""
        audio_str = payload.audio or ""
        
        cursor.execute(
            """
            INSERT INTO message_history 
            (chat_id, messenger, sender_id, text, images, audio, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.chat_id, 
                payload.chat_messenger, 
                str(payload.sender_id), 
                payload.text, 
                images_str, 
                audio_str, 
                timestamp
            )
        )
        
        # Get the last inserted message_id
        cursor.execute("SELECT last_insert_rowid()")
        new_message_id = cursor.fetchone()[0]
        
        # 2. Fetch all user messages from message_history table and map them to llm_answers
        cursor.execute(
            """
            SELECT mh.message_id, mh.text, mh.images, mh.audio, la.answer
            FROM message_history mh
            LEFT JOIN llm_answers la ON mh.message_id = la.message_id
            WHERE mh.chat_id = ? AND mh.sender_id = ?
            ORDER BY mh.timestamp ASC
            """,
            (payload.chat_id, str(payload.sender_id))
        )
        
        message_records = cursor.fetchall()
        
        # 3. Create message objects and append to messages list
        messages: List[Message] = []
        
        for record in message_records:
            # Add user message
            messages.append(
                Message(
                    sender="user",
                    text=record["text"],
                    images=record["images"].split(",") if record["images"] else None,
                    audio=record["audio"] if record["audio"] else None
                )
            )
            
            # Add assistant response if it exists
            if record["answer"]:
                messages.append(
                    Message(
                        sender="assistant",
                        text=record["answer"],
                        images=None,
                        audio=None
                    )
                )
        
        # 4. Create LLMProcessingPayloadSend
        processing_payload = LLMProcessingPayloadSend(
            sender_id=str(payload.sender_id),
            setting_id=setting_id,
            chat_id=payload.chat_id,
            messages=messages
        )
        
        # 5. Send to message processing server
        async with httpx.AsyncClient() as client:
            # FOR NOW MOCK
            # response = await client.post(
            #     f"{LLM_PROCESSING_SERVICE_URL}/process",
            #     json=processing_payload.model_dump()
            # )
            # response_data = response.json()
            response_data = {
                "answer": "test",
                "image": None,
                "clear_history": True,
                "ignore": False
            }
            llm_response = LLMProcessingPayloadSendResponse(**response_data)
        
        # 6. Handle the response
        if llm_response.clear_history:
            # Delete all messages from history by chat_id and sender_id
            cursor.execute(
                """
                DELETE FROM message_history
                WHERE chat_id = ? AND sender_id = ?
                """,
                (payload.chat_id, str(payload.sender_id))
            )
            db.commit()
        
        if not llm_response.ignore:
            # Save the LLM answer
            cursor.execute(
                """
                INSERT INTO llm_answers (answer, message_id)
                VALUES (?, ?)
                """,
                (llm_response.answer, new_message_id)
            )
            db.commit()

            # 7. Create and return LLMProcessingPayloadAnswer
            return LLMProcessingPayloadAnswer(
                answer=llm_response.answer,
                image=llm_response.image
            )
        
        return None