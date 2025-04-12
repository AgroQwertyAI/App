from fastapi import FastAPI
from src.routers.association import association_router
from src.routers.chat import chat_router
from src.routers.message_sending import message_sending_router
from src.routers.llm_processing import llm_processing_router
import logging
from src.init_db import init_db
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown events"""
    # Startup
    logger.info("Messenger API Service starting up...")
    init_db()
    logger.info("Messenger API Service started successfully")
    yield
    # Shutdown
    logger.info("Messenger API Service shutting down...")

app = FastAPI(
    title="Messenger API Service", 
    description="Messenger API Service",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(association_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(message_sending_router, prefix="/api")
app.include_router(llm_processing_router, prefix="/api")