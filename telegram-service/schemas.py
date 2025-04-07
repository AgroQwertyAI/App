from pydantic import BaseModel
from typing import Literal

class MessagePayload(BaseModel):
    source_name: str
    chat_id: int
    text: str
    sender_id: int = None
    sender_name: str
    image: str = None

class ChatRegistrationSchema(BaseModel):
    chat_id: int
    chat_name: str
    source_name: Literal['telegram'] = 'telegram'