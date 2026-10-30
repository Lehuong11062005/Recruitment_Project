from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel


class SkillRef(BaseModel):
    id: PydanticObjectId
    name: str
    category: Optional[str] = None


class AIAnalysisResponse(BaseModel):
    matched: List[SkillRef] = []      # kỹ năng CV có và JD yêu cầu
    missing: List[SkillRef] = []      # kỹ năng JD yêu cầu nhưng CV thiếu
    score_breakdown: Optional[Dict[str, float]] = None
    recommendation: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: PydanticObjectId
    job_id: PydanticObjectId
    candidate_id: PydanticObjectId
    cv_url: str
    pipeline_status: str
    ai_status: Literal["DONE", "SKIPPED", "FAILED"]   # AI chấm điểm được hay chưa
    ai_match_score: Optional[float] = None
    matching_version: Optional[str] = None
    ai_analysis: Optional[AIAnalysisResponse] = None
    parsed_text_preview: Optional[str] = None          # 300 ký tự đầu để kiểm tra nhanh
    applied_at: datetime
    job_title: Optional[str] = None
    company_name: Optional[str] = None


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


class StatusHistoryItem(BaseModel):
    status: str
    time: datetime


class ApplicationDetailResponse(ApplicationResponse):
    """GET /applications/{id}: ApplicationResponse + hồ sơ ứng viên + văn bản CV đầy đủ."""
    candidate: CandidateBrief
    cv_preview_url: str                      # /api/v1/applications/{id}/cv (stream PDF có phân quyền)
    cv_parsed_text: Optional[str] = None
    recruiter_note: Optional[str] = None     # chỉ HR mới thấy
    status_history: List[StatusHistoryItem] = []
