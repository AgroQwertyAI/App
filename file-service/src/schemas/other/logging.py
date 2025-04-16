from pydantic import BaseModel, Field
from typing import Literal

class LogSchema(BaseModel):
    message: str = Field(description="The message to log")
    level: Literal['info', 'error', 'warning'] = Field(description="The level of the log")
    source: str = Field(default='file-service', description="The source of the log")