from pydantic import BaseModel, Field
from typing import Literal

class SendingReportTo(BaseModel):
    phone_number: str = Field(description="The phone number of the message recipient", example="+79999999999")
    messenger: Literal["telegram", "whatsapp"] = Field(description="The messenger of the message recipient", example="whatsapp")