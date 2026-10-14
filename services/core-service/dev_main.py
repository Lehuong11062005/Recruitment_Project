"""
File chạy thử cục bộ: chỉ nạp Auth + Profile + Skills + Companies.
Dùng khi jobs.py / applications.py của các bạn khác còn trống.

Chạy:
    uvicorn dev_main:app --reload --port 8001

Tài liệu API:
    Swagger UI: http://localhost:8001/docs
    ReDoc:      http://localhost:8001/redoc
    OpenAPI:    http://localhost:8001/openapi.json
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import HTMLResponse

from app.core.database import init_db
from app.core.storage import mount_uploads
from app.routers import auth, skills, users, companies


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo database khi ứng dụng bắt đầu."""
    await init_db()
    yield


app = FastAPI(
    title="Core Service (DEV - Auth/Profile)",
    lifespan=lifespan,
    redoc_url=None,  # Tắt ReDoc mặc định để dùng endpoint tùy chỉnh
)


@app.get("/redoc", include_in_schema=False)
async def custom_redoc() -> HTMLResponse:
    """Hiển thị tài liệu API bằng ReDoc phiên bản cố định."""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url=(
            "https://cdn.jsdelivr.net/npm/"
            "redoc@2.5.0/bundles/redoc.standalone.js"
        ),
    )


# Authentication
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Auth"],
)

# Candidate / User Profile
app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["Users / Profile"],
)

# Skills
app.include_router(
    skills.router,
    prefix="/api/v1/skills",
    tags=["Skills"],
)

# Company Profile
app.include_router(
    companies.router,
    prefix="/api/v1",
    tags=["Company Profile"],
)

# Static files / uploaded files
mount_uploads(app)
