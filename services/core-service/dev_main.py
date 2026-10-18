"""File chạy THỬ cục bộ: nạp Auth + Profile + Skills + Companies + Applications.
Chạy:  uvicorn dev_main:app --reload --port 8001
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import init_db
from app.core.storage import mount_uploads
from app.routers import auth, skills, users, companies, applications


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Core Service (DEV - Auth/Profile/Apply)", lifespan=lifespan)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users / Profile"])
app.include_router(skills.router, prefix="/api/v1/skills", tags=["Skills"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Company Profile"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["Applications"])
mount_uploads(app)
