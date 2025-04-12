from fastapi import APIRouter, HTTPException
from src.schemas.endpoints.association import AssociationGet, AssociationPost
from src.session import get_db

association_router = APIRouter(tags=["Association"])

@association_router.get("/associations",
    status_code=200,
    response_model=list[AssociationGet],
    description="Get all associations of setting with chat which current bot is connected to"
)
async def get_associations():
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT association_id, chat_id, setting_id FROM associations")
        associations = cursor.fetchall()
        
        return [
            AssociationGet(
                association_id=association["association_id"],
                chat_id=association["chat_id"],
                setting_id=association["setting_id"]
            ) for association in associations
        ]


@association_router.post(
    "/association",
    status_code=201,
    response_model=AssociationGet,
    responses={404: {"description": "Chat not found"}},
    description="Add new association of setting with chat which current bot is connected to",
)
async def add_association(payload: AssociationPost):
    with get_db() as db:
        cursor = db.cursor()
        
        # Check if chat exists
        cursor.execute("SELECT 1 FROM chats WHERE chat_id = ?", (payload.chat_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Insert new association
        cursor.execute(
            "INSERT INTO associations (chat_id, setting_id) VALUES (?, ?)",
            (payload.chat_id, payload.setting_id)
        )
        
        # Get the last inserted row id
        association_id = cursor.lastrowid
        
        return AssociationGet(
            association_id=association_id,
            chat_id=payload.chat_id,
            setting_id=payload.setting_id
        )


@association_router.delete(
    "/association/{association_id}",
    status_code=204,
    response_model=None,
    responses={404: {"description": "Association not found"}},
    description="Delete association of setting with chat which current bot is connected to"
)
async def delete_association(association_id: int):
    with get_db() as db:
        cursor = db.cursor()
        
        # Check if association exists
        cursor.execute("SELECT 1 FROM associations WHERE association_id = ?", (association_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Association not found")
        
        # Delete association
        cursor.execute("DELETE FROM associations WHERE association_id = ?", (association_id,))
        
        return None