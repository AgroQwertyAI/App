from pydantic import BaseModel, Field
from typing import Literal

class ChatGet(BaseModel):
    chat_id: str = Field(description="The messenger chat id")
    name: str = Field(description="The name of the chat")
    messenger: Literal["telegram", "whatsapp"] = Field(description="The messenger of the chat")

class ChatPost(BaseModel):
    chat_id: str = Field(description="The messenger chat id")
    name: str = Field(description="The name of the chat")
    messenger: Literal["telegram", "whatsapp"] = Field(description="The messenger of the chat")
