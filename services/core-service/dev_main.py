"""File chạy THỬ cục bộ: chỉ nạp Auth + Profile + Skills.
Dùng khi jobs.py / applications.py của các bạn khác còn trống (main.py sẽ lỗi).
Chạy:  uvicorn dev_main:app --reload --port 8001
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import init_db
from app.core.storage import mount_uploads
from app.routers import auth, skills, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Core Service (DEV - Auth/Profile)", lifespan=lifespan)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users / Profile"])
app.include_router(skills.router, prefix="/api/v1/skills", tags=["Skills"])
mount_uploads(app)
