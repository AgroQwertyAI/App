from pydantic import Field, BaseModel
from datetime import datetime
from src.schemas.other.images import Images

class MessagePendingGet(BaseModel):
    message_id: int = Field(description="The unique identifier of the message")
    sender_phone_number: str = Field(description="The phone number of the message sender", example="+79999999999")
    sender_name: str = Field(description="The name of the message sender")
    sender_id: str = Field(description="The id of the message sender")
    
    setting_id: int = Field(description="The unique identifier of the setting to which the message belongs")

    original_message_text: str = Field(description="The original text of the message")
    formatted_message_text: dict = Field(
        description="The formatted json of the message", 
        example={"field1": ["value1", "value2"], "field2": ["value3", "value4"]}
    )

    timedata: datetime = Field(description="The timedata of the message")
    images: Images = Field(description="The images of the message")

    extra: dict = Field(description="The extra information about the message", example={})


class MessagePendingPost(BaseModel):
    sender_phone_number: str = Field(description="The phone number of the message sender", example="+79999999999")
    sender_name: str = Field(description="The name of the message sender")
    sender_id: str = Field(description="The id of the message sender")

    original_message_text: str = Field(description="The original text of the message")
    formatted_message_text: dict = Field(
        description="The formatted json of the message", 
        example={"field1": ["value1", "value2"], "field2": ["value3", "value4"]}
    )

    images: Images = Field(description="The images of the message")
    extra: dict = Field(
        description="The extra information about the message", 
        example={"testing": False, "datetime": "471418042025"}
    )


class MessagePendingPut(BaseModel):
    original_message_text: str | None = Field(None, description="The original text of the message")
    formatted_message_text: dict = Field(
        description="The formatted json of the message", 
        example={"field1": "value1", "field2": "value2"}
    )

    images: Images = Field(description="The images of the message")

    extra: dict = Field(description="The extra information about the message", example={})