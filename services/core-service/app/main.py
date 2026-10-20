from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import init_db
from app.core.storage import mount_uploads
from app.routers import auth, users, skills, applications, companies, jobs
from fastapi.middleware.cors import CORSMiddleware
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
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Hoặc ["*"] khi dev local
    allow_credentials=True,
    allow_methods=["*"],         # Cho phép tất cả HTTP methods (GET, POST, PUT, OPTIONS,...)
    allow_headers=["*"],         # Cho phép tất cả Headers (Authorization, Content-Type,...)
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users / Profile"])
app.include_router(skills.router, prefix="/api/v1/skills", tags=["Skills"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["Applications"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Company Profile"])

mount_uploads(app)  # phục vụ file CV đã upload tại /uploads

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "core-service"}
