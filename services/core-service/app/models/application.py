from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class StatusHistory(BaseModel):
    status: str
    changed_by: PydanticObjectId
    time: datetime = Field(default_factory=datetime.utcnow)

class AIAnalysis(BaseModel):
    matched: List[PydanticObjectId] = []
    missing: List[PydanticObjectId] = []
    score_breakdown: Optional[Dict[str, float]] = None
    recommendation: Optional[str] = None

class Application(Document):
    job_id: PydanticObjectId              # FK tham chiếu job_postings
    candidate_id: PydanticObjectId        # FK tham chiếu users
    cv_url: str
    parsed_text: Optional[str] = None     # Văn bản thô bóc tách từ PDF
    embedding_vector: Optional[List[float]] = None
    pipeline_status: str = "APPLIED"      # "APPLIED", "SCREENING", "INTERVIEW", "REJECTED", "HIRED"
    status_history: List[StatusHistory] = []
    interview_schedule: Optional[Dict[str, Any]] = None
    recruiter_note: Optional[str] = None
    ai_match_score: Optional[float] = None
    matching_version: Optional[str] = "v1.0"
    ai_analysis: Optional[AIAnalysis] = None
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "applications"
        indexes = [
            # unique=True thật sự: 1 ứng viên chỉ nộp 1 job 1 lần (bản cũ thiếu unique)
            IndexModel([("job_id", ASCENDING), ("candidate_id", ASCENDING)], unique=True),
            [("candidate_id", 1)],
            [("job_id", 1), ("ai_match_score", -1)],   # phục vụ xếp hạng ứng viên theo điểm (Tuần 9)
        ]
