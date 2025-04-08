from pydantic import BaseModel, Field
from typing import Literal, Optional

class MessagePayload(BaseModel):
    message_id: str
    source_name: str
    chat_id: str
    text: str
    sender_id: Optional[str] = None
    sender_name: str
    image: Optional[str] = Field(default=None)

class ChatRegistrationSchema(BaseModel):
    chat_id: str
    chat_name: str
    source_name: Literal['telegram'] = 'telegram'