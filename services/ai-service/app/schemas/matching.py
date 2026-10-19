from typing import List, Dict
from pydantic import BaseModel, Field


class ParseCVResponse(BaseModel):
    status: str = "success"
    filename: str
    parsed_text: str
    skills: List[str] = Field(default_factory=list)
    extracted_skills: List[str] = Field(default_factory=list)
    embedding_vector: List[float] = Field(default_factory=list)


class MatchingRequest(BaseModel):
    cv_text: str
    jd_text: str
    candidate_skills: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    candidate_experience_years: float = 0.0
    job_experience_required: float = 0.0


class AIAnalysisBreakdown(BaseModel):
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    recommendation: str = ""


class MatchingResponse(BaseModel):
    ai_match_score: float
    matching_version: str
    embedding_vector: List[float] = Field(default_factory=list)
    ai_analysis: AIAnalysisBreakdown


class EmbeddingRequest(BaseModel):
    text: str


class EmbeddingResponse(BaseModel):
    embedding: List[float]
    model_version: str