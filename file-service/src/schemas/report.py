from pydantic import Field, BaseModel
from datetime import datetime

class ReportGet(BaseModel):
    report_id: int = Field(description="The unique identifier of the report")
    setting_id: int = Field(description="The unique identifier of the setting to which the report belongs")

    timedata: datetime = Field(description="The timedata of the report")
    file: str = Field(description="The base64 encoded file of the report", example="base64,<file>")

    extra: dict = Field(description="The extra information about the report", example={})