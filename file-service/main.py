from fastapi import FastAPI
from src.routers.settings import settings_router
from src.routers.message_pending import message_pending_router
from src.routers.message_report import message_report_router
from src.routers.report import report_router


app = FastAPI(title="File Service", description="File Service")

app.include_router(settings_router, prefix="/api")
app.include_router(message_pending_router, prefix="/api")
app.include_router(message_report_router, prefix="/api")
app.include_router(report_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)