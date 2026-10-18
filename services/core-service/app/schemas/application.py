from datetime import datetime
from typing import Dict, List, Literal, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel


class SkillRef(BaseModel):
    id: PydanticObjectId
    name: str


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
