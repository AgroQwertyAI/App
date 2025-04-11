from pydantic import Field, BaseModel
from typing import Literal
from src.schemas.other.sending import SendingReportTo


class SettingGet(BaseModel):
    setting_id: int = Field(description="The unique identifier of the setting")
    setting_name: str = Field(description="The name of the setting")
    setting_description: str = Field(description="The optional description of the setting")
    format_report: Literal["xlsx"] = Field(description="The format to which write final report")
    type: Literal["filesystem", "google-drive", "yandex-disk"] = Field(description="The file storage type")

    send_to: list[SendingReportTo] = Field(description="The list of phone numbers and their messengers to send the report to")

    minute: str = Field(description="CRON minute to send the report", example="0")
    hour: str = Field(description="CRON hour to send the report", example="6")
    day_of_month: str = Field(description="CRON day of the month to send the report", example="*")
    month: str = Field(description="CRON month to send the report", example="*")
    day_of_week: str = Field(description="CRON day of the week to send the report", example="*")

    deleted: bool = Field(description="Whether the setting is deleted", example=False)

    extra: dict = Field(description="The extra information about the setting", example={})


class SettingPost(BaseModel):
    setting_name: str = Field(description="The name of the setting")
    setting_description: str = Field(description="The optional description of the setting")
    format_report: Literal["xlsx"] = Field(description="The format to which write final report")
    type: Literal["filesystem", "google-drive", "yandex-disk"] = Field(description="The file storage type")

    send_to: list[SendingReportTo] = Field(description="The list of phone numbers and their messengers to send the report to")

    minute: str = Field(description="CRON minute to send the report", example="0")
    hour: str = Field(description="CRON hour to send the report", example="6")
    day_of_month: str = Field(description="CRON day of the month to send the report", example="*")
    month: str = Field(description="CRON month to send the report", example="*")
    day_of_week: str = Field(description="CRON day of the week to send the report", example="*")

    extra: dict = Field(description="The extra information about the setting", example={})


class SettingPut(SettingPost):
    setting_name: str = Field(description="The name of the setting")
    setting_description: str = Field(description="The optional description of the setting")
    format_report: Literal["xlsx"] = Field(description="The format to which write final report")
    type: Literal["filesystem", "google-drive", "yandex-disk"] = Field(description="The file storage type")

    send_to: list[SendingReportTo] = Field(description="The list of phone numbers and their messengers to send the report to")

    minute: str = Field(description="CRON minute to send the report", example="0")
    hour: str = Field(description="CRON hour to send the report", example="6")
    day_of_month: str = Field(description="CRON day of the month to send the report", example="*")
    month: str = Field(description="CRON month to send the report", example="*")
    day_of_week: str = Field(description="CRON day of the week to send the report", example="*")

    extra: dict = Field(description="The extra information about the setting", example={})