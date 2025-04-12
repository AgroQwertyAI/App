from pydantic import BaseModel, Field

class AssociationGet(BaseModel):
    association_id: int = Field(description="The id of the association")
    chat_id: str = Field(description="The id of the chat")
    setting_id: int = Field(description="The id of the setting")

class AssociationPost(BaseModel):
    chat_id: str = Field(description="The id of the chat")
    setting_id: int = Field(description="The id of the setting")
