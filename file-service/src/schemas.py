from pydantic import BaseModel
from typing import Literal
from pydantic import Field

class CronArgs(BaseModel):
    folder_name: str
    format: Literal["csv", "xml"]
    chat_id: str
    type: Literal["drive", "filesystem"]

class CronSchedule(BaseModel):
    minute: int = Field(ge=0, le=59)
    hour: int = Field(ge=0, le=23)
    day_of_month: int = Field(ge=1, le=31)
    month: int = Field(ge=1, le=12)
    day_of_week: int = Field(ge=0, le=6)

class CronJob(BaseModel):
    type: Literal["drive", "filesystem"]
    chat_id: str
    format: Literal["csv", "xml"]
    folder_name: str
    
    minute: int = Field(ge=0, le=59)
    hour: int = Field(ge=0, le=23)
    day_of_month: int = Field(ge=1, le=31)
    month: int = Field(ge=1, le=12)
    day_of_week: int = Field(ge=0, le=6)
