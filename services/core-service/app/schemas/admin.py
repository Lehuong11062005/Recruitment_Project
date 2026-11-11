from typing import Dict
from pydantic import BaseModel, Field


class UserStatistics(BaseModel):
    total: int = 0
    candidates: int = 0
    recruiters: int = 0
    admins: int = 0
    active: int = 0
    banned: int = 0
    by_user_type: Dict[str, int] = Field(default_factory=dict)
    by_status: Dict[str, int] = Field(default_factory=dict)


class CompanyStatistics(BaseModel):
    total: int = 0
    pending: int = 0
    verified: int = 0
    rejected: int = 0
    by_verification_status: Dict[str, int] = Field(default_factory=dict)


class JobStatistics(BaseModel):
    total: int = 0
    open: int = 0
    closed: int = 0
    hidden: int = 0
    by_status: Dict[str, int] = Field(default_factory=dict)


class ApplicationStatistics(BaseModel):
    total: int = 0
    applied: int = 0
    screening: int = 0
    interview: int = 0
    hired: int = 0
    rejected: int = 0
    by_pipeline_status: Dict[str, int] = Field(default_factory=dict)


class AIMatchingStatistics(BaseModel):
    total_scored: int = 0
    average_score: float = 0.0
    score_distribution: Dict[str, int] = Field(default_factory=dict)
    by_matching_version: Dict[str, int] = Field(default_factory=dict)
    by_ai_status: Dict[str, int] = Field(default_factory=dict)


class AdminStatisticsResponse(BaseModel):
    users: UserStatistics
    companies: CompanyStatistics
    jobs: JobStatistics
    applications: ApplicationStatistics
    ai_matching: AIMatchingStatistics
