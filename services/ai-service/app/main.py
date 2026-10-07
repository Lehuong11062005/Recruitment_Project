from fastapi import FastAPI
from app.routers import ai_matching

app = FastAPI(
    title="Recruitment AI Service",
    description="Dịch vụ xử lý NLP và Matching",
    version="1.0.0"
)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "ai-service"}