from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field

class CandidateProfile(BaseModel):
    summary: Optional[str] = None
    skills: List[PydanticObjectId] = []  # FK tham chiếu skills_taxonomy
    experience: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []
    location: Optional[str] = None
    phone: Optional[str] = None
    cv_url: Optional[str] = None
    candidate_embedding: Optional[List[float]] = None  # Phục vụ Vector Search gợi ý việc làm

class User(Document):
    email: Indexed(EmailStr, unique=True)
    password_hash: str
    full_name: str
    phone: Optional[str] = None
    role: str = "USER"  # "USER" hoặc "ADMIN"
    user_type: Optional[str] = None  # "CANDIDATE", "RECRUITER", hoặc None
    company_id: Optional[PydanticObjectId] = None  # FK companies, chỉ dành cho RECRUITER
    profile: Optional[CandidateProfile] = None     # Chỉ dành cho CANDIDATE
    status: str = "ACTIVE"  # "ACTIVE", "BANNED"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None          # Soft delete

    class Settings:
        name = "users"
        indexes = [
            [("company_id", 1)],
        ]