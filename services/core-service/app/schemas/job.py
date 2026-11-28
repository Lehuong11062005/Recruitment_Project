import math
from typing import Any, Dict, List, Optional
from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_SKILL_WEIGHT = 0.50
DEFAULT_SEMANTIC_WEIGHT = 0.35
DEFAULT_EXPERIENCE_WEIGHT = 0.15


class MatchingWeightsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_weight: float
    semantic_weight: float
    experience_weight: float

    @field_validator("skill_weight", "semantic_weight", "experience_weight", mode="before")
    @classmethod
    def _validate_weight(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Trọng số phải là số hợp lệ.")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("Trọng số phải là số hữu hạn.")
        if numeric < 0.0 or numeric > 1.0:
            raise ValueError("Mỗi trọng số phải nằm trong khoảng từ 0 đến 1.")
        return round(numeric, 4)

    @model_validator(mode="after")
    def _validate_sum(self) -> "MatchingWeightsSchema":
        total = self.skill_weight + self.semantic_weight + self.experience_weight
        if total <= 0.0 or abs(total - 1.0) > 1e-4:
            raise ValueError(
                "Tổng ba trọng số (skill_weight + semantic_weight + experience_weight) phải bằng 1.0 (100%)."
            )
        return self

    @classmethod
    def default(cls) -> "MatchingWeightsSchema":
        return cls(
            skill_weight=DEFAULT_SKILL_WEIGHT,
            semantic_weight=DEFAULT_SEMANTIC_WEIGHT,
            experience_weight=DEFAULT_EXPERIENCE_WEIGHT,
        )


def resolve_matching_weights(raw: Any) -> MatchingWeightsSchema:
    """Chuẩn hóa trọng số từ JobPosting (hoặc trả về mặc định 0.50/0.35/0.15 cho bản ghi cũ)."""
    if raw is None:
        return MatchingWeightsSchema.default()
    if isinstance(raw, MatchingWeightsSchema):
        return raw
    if hasattr(raw, "model_dump"):
        data = raw.model_dump()
    elif isinstance(raw, dict):
        data = raw
    else:
        return MatchingWeightsSchema.default()
    if not data:
        return MatchingWeightsSchema.default()
    try:
        return MatchingWeightsSchema.model_validate(data)
    except Exception:
        return MatchingWeightsSchema.default()


class JobCreateSchema(BaseModel):
    title: str
    description: str
    required_skills: List[PydanticObjectId] = Field(default_factory=list)
    level: Optional[str] = "MID"
    experience_required: int = 0
    salary: Optional[Dict[str, Any]] = None
    location: Optional[str] = None
    matching_weights: Optional[MatchingWeightsSchema] = None


class JobUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[PydanticObjectId]] = None
    level: Optional[str] = None
    experience_required: Optional[int] = None
    salary: Optional[Dict[str, Any]] = None
    location: Optional[str] = None
    matching_weights: Optional[MatchingWeightsSchema] = None

    @model_validator(mode="after")
    def _reject_explicit_null_weights(self) -> "JobUpdateSchema":
        if "matching_weights" in self.model_fields_set and self.matching_weights is None:
            raise ValueError("matching_weights không được để giá trị null.")
        return self


class JobStatusUpdateSchema(BaseModel):
    status: str  # "OPEN", "CLOSED", "HIDDEN"
