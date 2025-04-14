from src.config import BACKEND_SERVICE_URL, logger
from src.schemas.other.logging import LogSchema
from typing import Literal
import httpx

def log_info(message: str, level: Literal['info', 'error', 'warning']):
    if level == 'info':
        logger.info(message)
    elif level == 'error':
        logger.error(message)
    elif level == 'warning':
        logger.warning(message)

    with httpx.Client() as client:
        try:
            client.post(
                f"{BACKEND_SERVICE_URL}/logs",
                json=LogSchema(message=message, level=level).model_dump()
            )
        except Exception as e:
            logger.error(f"Failed to send log to backend service: {e}")