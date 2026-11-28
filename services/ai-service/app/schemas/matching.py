import math
from typing import Any, Dict, List, Optional
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.config import settings


class MatchingWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_weight: float
    semantic_weight: float
    experience_weight: float

    @field_validator("skill_weight", "semantic_weight", "experience_weight", mode="before")
    @classmethod
    def _validate_weight(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Trọng số phải là kiểu số hợp lệ.")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("Trọng số phải là số hữu hạn.")
        if numeric < 0.0 or numeric > 1.0:
            raise ValueError("Mỗi trọng số phải nằm trong khoảng từ 0 đến 1.")
        return round(numeric, 4)

    @model_validator(mode="after")
    def _validate_total(self) -> "MatchingWeights":
        total = self.skill_weight + self.semantic_weight + self.experience_weight
        if total <= 0.0 or abs(total - 1.0) > 1e-4:
            raise ValueError(
                "Tổng ba trọng số (skill_weight + semantic_weight + experience_weight) phải bằng 1.0 (100%)."
            )
        return self

    @classmethod
    def default(cls) -> "MatchingWeights":
        return cls(
            skill_weight=settings.SKILL_WEIGHT,
            semantic_weight=settings.SEMANTIC_WEIGHT,
            experience_weight=settings.EXPERIENCE_WEIGHT,
        )


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
    matching_weights: Optional[MatchingWeights] = None

    @model_validator(mode="before")
    @classmethod
    def _accept_weights_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "matching_weights" not in data and "weights" in data:
            copied = dict(data)
            copied["matching_weights"] = copied.pop("weights")
            return copied
        return data


class AIAnalysisBreakdown(BaseModel):
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    recommendation: str = ""


class MatchingResponse(BaseModel):
    ai_match_score: float
    matching_version: str
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    matching_weights_snapshot: MatchingWeights = Field(default_factory=MatchingWeights.default)
    embedding_vector: List[float] = Field(default_factory=list)
    ai_analysis: AIAnalysisBreakdown


class EmbeddingRequest(BaseModel):
    text: str


class EmbeddingResponse(BaseModel):
    embedding: List[float]
    model_version: str
