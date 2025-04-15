from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class MessagePayload(BaseModel):
    message_id: str = Field(description="The id of the message")
    source_name: Literal['telegram'] = Field(default='telegram', description="The source of the message")
    chat_id: str = Field(description="The id of the chat")
    text: str | None = Field(default=None, description="The text message received from sender")
    sender_id: Optional[str] = Field(default=None, description="The id of the sender")
    sender_name: str | None = Field(default=None, description="The name of the sender")
    is_private: bool = Field(default=False, description="Whether the message is not from a group")

    audio: Optional[str] = Field(default=None, description="The base64 encoded audio received from sender. Has OGG mime type")
    images: list[str] = Field(default=[], description="The base64 encoded images received from sender. Has JPEG mime type")

class ChatRegistrationSchema(BaseModel):
    chat_id: str = Field(description="The id of the chat")
    chat_name: str = Field(description="The name of the chat")
    source_name: Literal['telegram'] = Field(default='telegram', description="The source of the chat")

class SendMessageText(BaseModel):
    chat_id: str = Field(description="The id of the chat")
    text: str = Field(description="The text to send")

class SendMessageImage(BaseModel):
    chat_id: str = Field(description="The id of the chat")
    image: str = Field(description="The base64 encoded image to send")

class SendMessageFile(BaseModel):
    chat_id: str = Field(description="The id of the chat")
    file: str = Field(description="The base64 encoded file to send")
    filename: Optional[str] = Field(default=None, description="The name of the file")
    caption: Optional[str] = Field(default=None, description="The caption of the file")
    mimetype: Optional[str] = Field(default=None, description="The mime type of the file")

class LogSchema(BaseModel):
    message: str = Field(description="The message to log")
    level: Literal['info', 'error', 'warning'] = Field(description="The level of the log")
    source: str = Field(default='telegram', description="The source of the log")

class MappingSchema(BaseModel):
    chat_id: str = Field(description="The id of the chat")
    phone_number: str = Field(description="The phone number of the chat")
    created_at: datetime = Field(description="The creation date of the mapping")
