
from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document, PydanticObjectId
from pydantic import Field

class JobPosting(Document):
    company_id: PydanticObjectId          # FK tham chiếu companies
    recruiter_id: PydanticObjectId        # FK tham chiếu users (Người tạo tin)
    title: str
    description: str
    required_skills: List[PydanticObjectId] = []  # FK tham chiếu skills_taxonomy
    level: Optional[str] = "MID"                  # "JUNIOR", "MID", "SENIOR"
    experience_required: int = 0
    salary: Optional[Dict[str, Any]] = None       # {"min": 1000, "max": 2000, "currency": "VND"}
    location: Optional[str] = None
    job_embedding_vector: Optional[List[float]] = None
    embedding_model: Optional[str] = "all-MiniLM-L6-v2"
    views_count: int = 0
    applications_count: int = 0
    status: str = "OPEN"                          # "OPEN", "CLOSED", "HIDDEN"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    class Settings:
        name = "job_postings"
        indexes = [
            [("title", "text"), ("description", "text")],
            [("company_id", 1), ("deleted_at", 1)],
            [("recruiter_id", 1)],
        ]