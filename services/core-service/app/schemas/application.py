from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from app.schemas.job import MatchingWeightsSchema
from app.schemas.notification import UTCDatetime


class SkillRef(BaseModel):
    id: PydanticObjectId
    name: str
    category: Optional[str] = None


class AIAnalysisResponse(BaseModel):
    matched: List[SkillRef] = Field(default_factory=list)      # kỹ năng CV có và JD yêu cầu
    missing: List[SkillRef] = Field(default_factory=list)      # kỹ năng JD yêu cầu nhưng CV thiếu
    matched_skills: List[SkillRef] = Field(default_factory=list)
    missing_skills: List[SkillRef] = Field(default_factory=list)
    score_breakdown: Optional[Dict[str, float]] = None
    recommendation: Optional[str] = None


class StatusHistoryItem(BaseModel):
    status: str
    time: UTCDatetime
    changed_by: Optional[PydanticObjectId] = None   # ai đổi trạng thái (HR / Candidate khi nộp)


class ApplicationJobBrief(BaseModel):
    id: PydanticObjectId
    title: str
    location: Optional[str] = None
    level: Optional[str] = None
    salary: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    is_deleted: bool = False


class ApplicationCompanyBrief(BaseModel):
    id: PydanticObjectId
    name: str
    logo_url: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    verification_status: Optional[str] = None
    is_deleted: bool = False


class ApplicationResponse(BaseModel):
    id: PydanticObjectId
    job_id: PydanticObjectId
    candidate_id: PydanticObjectId
    cv_url: str
    pipeline_status: str
    status_history: List[StatusHistoryItem] = Field(default_factory=list)
    interview_schedule: Optional[Dict[str, Any]] = None
    ai_status: Literal[
        "DONE", "SKIPPED", "FAILED", "PENDING", "PROCESSING"
    ]   # AI chấm điểm được hay chưa
    ai_match_score: Optional[float] = None
    matching_version: Optional[str] = None
    score_breakdown: Optional[Dict[str, float]] = None
    matching_weights_snapshot: Optional[MatchingWeightsSchema] = None
    ai_analysis: Optional[AIAnalysisResponse] = None
    ai_analyzed_at: Optional[datetime] = None
    parsed_text_preview: Optional[str] = None          # 300 ký tự đầu để kiểm tra nhanh
    applied_at: datetime
    updated_at: Optional[datetime] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    job: Optional[ApplicationJobBrief] = None
    company: Optional[ApplicationCompanyBrief] = None


class CandidateBrief(BaseModel):
    """Thông tin ứng viên hiển thị ở màn hình chi tiết của HR."""
    id: PydanticObjectId
    full_name: str
    email: str
    phone: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    skills: List[SkillRef] = []
    experience: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []


class ApplicationDetailResponse(ApplicationResponse):
    """GET /applications/{id}: ApplicationResponse + hồ sơ ứng viên + văn bản CV đầy đủ."""
    candidate: CandidateBrief
    cv_preview_url: str                      # /api/v1/applications/{id}/cv (stream PDF có phân quyền)
    cv_parsed_text: Optional[str] = None
    recruiter_note: Optional[str] = None     # chỉ HR mới thấy


class RankedSkillItem(BaseModel):
    id: PydanticObjectId
    name: str


class RankedApplicationItem(BaseModel):
    id: PydanticObjectId
    candidate_id: PydanticObjectId
    full_name: str
    email: str
    phone: Optional[str] = None
    ai_match_score: Optional[float] = None
    ai_status: Optional[str] = None
    matching_version: Optional[str] = None
    score_breakdown: Optional[Dict[str, float]] = None
    matching_weights_snapshot: Optional[MatchingWeightsSchema] = None
    pipeline_status: str
    applied_at: datetime
    matched_skills: List[RankedSkillItem] = Field(default_factory=list)
    missing_skills: List[RankedSkillItem] = Field(default_factory=list)
    cv_preview_url: str

PipelineStatus = Literal["APPLIED", "SCREENING", "INTERVIEW", "HIRED", "REJECTED"]


class InterviewScheduleIn(BaseModel):
    """Lịch phỏng vấn HR gửi lên: { time, location, link }."""
    time: datetime
    location: Optional[str] = Field(default=None, max_length=300)
    link: Optional[str] = Field(default=None, max_length=500)


class ApplicationStatusUpdate(BaseModel):
    """Body của PATCH /api/v1/applications/{application_id}/status."""
    pipeline_status: PipelineStatus
    recruiter_note: Optional[str] = Field(default=None, max_length=5000)
    interview_schedule: Optional[InterviewScheduleIn] = None


class ApplicationStatusResponse(BaseModel):
    id: PydanticObjectId
    pipeline_status: PipelineStatus
    recruiter_note: Optional[str] = None
    interview_schedule: Optional[Dict[str, Any]] = None
    status_history: List[StatusHistoryItem] = Field(default_factory=list)
    updated_at: datetime

