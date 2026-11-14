from datetime import datetime
from typing import Dict, Generic, Literal, TypeVar

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

Item = TypeVar("Item")


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


class AdminPage(BaseModel, Generic[Item]):
    items: list[Item]
    total: int
    page: int
    limit: int


class AdminUserItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    full_name: str
    email: str
    role: str
    user_type: str | None
    status: str


class AdminCompanyItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    name: str
    industry: str | None
    address: str | None
    website: str | None
    description: str | None
    verification_status: str


class AdminJobItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PydanticObjectId
    title: str
    description: str
    company_id: PydanticObjectId
    company_name: str | None = None
    location: str | None
    status: str
    deleted_at: datetime | None


class AdminUserStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "BANNED"]


class AdminCompanyVerificationUpdate(BaseModel):
    verification_status: Literal["VERIFIED", "REJECTED"]


class AdminJobStatusUpdate(BaseModel):
    status: Literal["HIDDEN", "DELETED"]
