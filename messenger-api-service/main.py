from fastapi import FastAPI
from src.routers.llm_processing import llm_processing_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Messenger API Service", 
    description="Messenger API Service",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(llm_processing_router, prefix="/api")
