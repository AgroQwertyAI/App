from pydantic import BaseModel, Field
from typing import Literal

class LLMProcessingPayloadPost(BaseModel):
    message_id: str = Field(description="The id of the message")
    source_name: Literal["telegram", "whatsapp"] = Field(description="The messenger of the chat")
    chat_id: str = Field(description="The id of the chat")

    text: str = Field(description="The text message received from sender")

    sender_id: str = Field(description="The id of the sender")
    sender_name: str = Field(description="The name of the sender")

    is_private: bool = Field(description="Whether the message is private")
    images: list[str] | None = Field(description="The base64 encoded images received from sender. Has JPEG mime type")
    audio: str | None = Field(description="The base64 encoded audio received from sender. Has OGG mime type")

class LLMProcessingPayloadPostResponse(BaseModel):
    message_id: str = Field(description="The id of the message")
    source_name: Literal["telegram", "whatsapp"] = Field(description="The messenger of the chat")
    chat_id: str = Field(description="The id of the chat")

    text: str = Field(description="The text message received from sender")

    sender_id: str = Field(description="The id of the sender")
    sender_name: str = Field(description="The name of the sender")

    is_private: bool = Field(description="Whether the message is private")
    images: list[str] | None = Field(description="The base64 encoded images received from sender. Has JPEG mime type")