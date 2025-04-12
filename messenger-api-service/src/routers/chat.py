from fastapi import APIRouter, HTTPException, Depends
from src.schemas.endpoints.chat import ChatGet, ChatPost
from src.session import get_db
import sqlite3

chat_router = APIRouter(tags=["Chat"])

@chat_router.get(
    "/chats",
    status_code=200,
    response_model=list[ChatGet],
    description="Get all chats which current bot is connected to"
)
async def get_chats():
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT chat_id, chat_name as name, messenger FROM chats")
        chats = [dict(row) for row in cursor.fetchall()]
        return chats


@chat_router.post(
    "/chat",
    status_code=201,
    response_model=ChatGet,
    description="Add new chat to current bot. Executes when bot joins the chat",
    responses={409: {"description": "Chat with id already exists"}}
)
async def add_chat(payload: ChatPost):
    with get_db() as db:
        cursor = db.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO chats (chat_id, chat_name, messenger) VALUES (?, ?, ?)",
                (payload.chat_id, payload.name, payload.messenger)
            )
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(
                    status_code=409,
                    detail=f"Chat with id {payload.chat_id} already exists"
                )
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        return {
            "chat_id": payload.chat_id,
            "name": payload.name,
            "messenger": payload.messenger
        }


@chat_router.delete(
    "/chat/{chat_id}",
    status_code=204,
    response_model=None,
    responses={404: {"description": "Chat not found"}},
    description="Delete chat from current bot. Executes when bot leaves the chat"
)
async def delete_chat(chat_id: str):
    with get_db() as db:
        cursor = db.cursor()
        
        # Check if chat exists
        cursor.execute("SELECT 1 FROM chats WHERE chat_id = ?", (chat_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Delete chat (associations will be deleted via CASCADE)
        cursor.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
        
        return None