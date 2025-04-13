from pydantic import BaseModel, Field
from typing import Literal, Optional

class MessagePayload(BaseModel):
    message_id: str
    source_name: Literal['telegram'] = 'telegram'
    chat_id: str
    text: str | None = None
    sender_id: Optional[str] = None
    sender_name: str | None = None
    is_private: bool

    audio: Optional[str] = Field(default=None)
    images: list[str] = Field(default=[])

class ChatRegistrationSchema(BaseModel):
    chat_id: str
    chat_name: str
    source_name: Literal['telegram'] = 'telegram'