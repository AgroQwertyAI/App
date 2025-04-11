from fastapi import FastAPI
from src.routers.settings import settings_router
from src.routers.messages_pending import message_pending_router
from src.routers.messages_report import message_report_router
from src.routers.reports import report_router
from src.routers.cloud_config import cloud_config_router
import logging
from src.init_db import init_db
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown events"""
    # Startup
    logger.info("File Service starting up...")
    init_db()
    logger.info("File Service started successfully")
    yield
    # Shutdown
    logger.info("File Service shutting down...")

app = FastAPI(title="File Service", description="File Service", lifespan=lifespan)

app.include_router(settings_router, prefix="/api")
app.include_router(message_pending_router, prefix="/api")
app.include_router(message_report_router, prefix="/api")
app.include_router(report_router, prefix="/api")
app.include_router(cloud_config_router, prefix="/api")