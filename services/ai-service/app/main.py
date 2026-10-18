from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.core.model_loader import ModelLoader
from app.routers import ai_matching


@asynccontextmanager
async def lifespan(app: FastAPI):
    ModelLoader.load_model()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.include_router(ai_matching.router, prefix="/api/v1/ai", tags=["AI Engine"])


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "ai-service",
        "model": settings.MODEL_NAME,
    }