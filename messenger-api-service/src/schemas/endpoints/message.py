from pydantic import BaseModel, Field
from typing import Literal

class MessagePayloadPost(BaseModel):
    text: str = Field(description="The text message to send to receiver")
    base64_file: str | None = Field(description="The base64 encoded file to send")
    document_mime_type: Literal["xlsx"] = Field(description="The mime type of the document to send")

    chat_messenger: Literal["telegram", "whatsapp"] = Field(description="The messenger of the chat")
    chat_id: str = Field(description="The id of the chat")