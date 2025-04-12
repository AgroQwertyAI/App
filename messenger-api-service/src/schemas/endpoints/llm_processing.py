from pydantic import BaseModel, Field
from typing import Literal

class LLMProcessingPayloadPost(BaseModel):
    chat_id: str = Field(description="The id of the chat")
    chat_messenger: Literal["telegram", "whatsapp"] = Field(description="The messenger of the chat")

    sender_id: int = Field(description="The id of the sender")
    sender_name: str = Field(description="The name of the sender")
    sender_phone_number: str = Field(description="The phone number of the sender")

    text: str = Field(description="The text message received from sender")
    images: list[str] | None = Field(description="The images received from sender")
    audio: str | None = Field(description="The audio received from sender")

class Message(BaseModel):
    sender: Literal["user", "assistant"] = Field(description="The sender of the message")

    text: str = Field(description="The text message received from sender")
    images: list[str] | None = Field(description="The images received from sender")
    audio: str | None = Field(description="The audio received from sender")

class LLMProcessingPayloadSend(BaseModel):
    sender_id: str = Field(description="The id of the sender")
    chat_id: str = Field(description="The id of the chat")
    setting_id: int = Field(description="The id of the setting")

    messages: list[Message] = Field(description="The messages to send")

class LLMProcessingPayloadSendResponse(BaseModel):
    answer: str = Field(description="The text feedback from LLM")
    image: str | None = Field(description="The image feedback from LLM")

    ignore: bool = Field(description="Whether to ignore received message")
    clear_history: bool = Field(description="Whether to clear the history")

class LLMProcessingPayloadAnswer(BaseModel):
    answer: str = Field(description="The text feedback from LLM")
    image: str | None = Field(description="The image feedback from LLM")