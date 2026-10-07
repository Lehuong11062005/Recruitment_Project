from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import init_db
from app.routers import auth, jobs, applications

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="Recruitment Platform - Core Service",
    description="Backend xử lý nghiệp vụ chính và cơ sở dữ liệu MongoDB",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["Applications"])

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "core-service"}