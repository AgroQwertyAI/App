from fastapi import APIRouter, HTTPException
from src.schemas.llm_processing import LLMProcessingPayloadPost, LLMProcessingPayloadPostResponse
import httpx
from src.whisper import transcribe_audio
import logging
from src.config import MESSAGE_PROCESSING_SERVICE_URL

logger = logging.getLogger(__name__)

llm_processing_router = APIRouter(tags=["LLM Processing"])

@llm_processing_router.post("/llm_processing",
    status_code=200,
    response_model=LLMProcessingPayloadPostResponse,
    description="Process message received from messenger and send it to message processing service",
)
async def llm_processing(payload: LLMProcessingPayloadPost):
    transcribed_text = transcribe_audio(payload.audio)

    response = LLMProcessingPayloadPostResponse(
        source_name=payload.source_name,
        chat_id=payload.chat_id,
        text=payload.text + "\n\n" + transcribed_text,
        sender_id=payload.sender_id,
        sender_name=payload.sender_name,
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MESSAGE_PROCESSING_SERVICE_URL}/api/new_message",
            json=response.model_dump(),
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return None