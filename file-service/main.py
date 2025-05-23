from fastapi import FastAPI
from src.routers.settings import settings_router
from src.routers.messages_pending import message_pending_router
from src.routers.messages_report import message_report_router
from src.routers.reports import report_router
from src.routers.cloud_config import cloud_config_router
from src.routers.management import management_router
from src.init_db import init_db
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from src.auxiliary.logging import log_info

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown events"""
    # Startup
    init_db()
    log_info("File service started", 'info')
    yield
    # Shutdown
    log_info("File service ended", 'info')

app = FastAPI(title="File Service", description="File Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings_router, prefix="/api")
app.include_router(message_pending_router, prefix="/api")
app.include_router(message_report_router, prefix="/api")
app.include_router(report_router, prefix="/api")
app.include_router(cloud_config_router, prefix="/api")
app.include_router(management_router, prefix="/api")