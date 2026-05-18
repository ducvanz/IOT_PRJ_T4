import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
from pathlib import Path

from app.core.config import settings

# Ensure required directories exist (prevents startup crash)
Path("dashboard/static/css").mkdir(parents=True, exist_ok=True)
Path("dashboard/static/js").mkdir(parents=True, exist_ok=True)
Path("dashboard/templates").mkdir(parents=True, exist_ok=True)
from app.core.database import init_db
from app.api.v1.router import api_router
from app.mqtt.client import mqtt_manager
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting NexusIoT Platform...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start MQTT client
    if settings.MQTT_ENABLED:
        await mqtt_manager.connect()
        logger.info("MQTT client connected")

    yield

    # Shutdown
    logger.info(" Shutting down NexusIoT Platform...")
    if settings.MQTT_ENABLED:
        await mqtt_manager.disconnect()


app = FastAPI(
    title="NexusIoT Platform",
    description="IoT Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for dashboard
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Include WebSocket routes
from app.api.v1.endpoints.websocket import ws_router
app.include_router(ws_router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve dashboard"""
    return FileResponse("dashboard/templates/index.html")


@app.get("/health")
async def health_check():
    return {"status": "ok", "platform": "NexusIoT", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
