from pydantic import BaseModel, Field

class Images(BaseModel):
    images: list[str] = Field(description="The images of the message", example=["base64,<image1>", "base64,<image2>"])
