from typing import List, Literal, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- AUTH ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Tối thiểu 8 ký tự, tối đa 72 byte")
    full_name: str = Field(min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    user_type: Literal["CANDIDATE", "RECRUITER"]

    @field_validator("password")
    @classmethod
    def password_not_too_long(cls, v: str) -> str:
        # bcrypt chỉ xử lý tối đa 72 byte
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Mật khẩu tối đa 72 byte (khoảng 72 ký tự không dấu)")
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Họ tên không được để trống")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: PydanticObjectId
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str                       # "USER" | "ADMIN"
    user_type: Optional[str] = None  # "CANDIDATE" | "RECRUITER" | None
    company_id: Optional[PydanticObjectId] = None
    status: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------- PROFILE ỨNG VIÊN ----------
class ExperienceItem(BaseModel):
    company: str
    position: str
    years: Optional[float] = Field(default=None, ge=0, le=60)
    description: Optional[str] = None


class EducationItem(BaseModel):
    school: str
    major: Optional[str] = None
    graduation_year: Optional[int] = Field(default=None, ge=1950, le=2100)


class ProfileUpdate(BaseModel):
    """Chỉ gửi những trường muốn đổi, trường nào không gửi sẽ được giữ nguyên."""
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=2000)
    location: Optional[str] = Field(default=None, max_length=200)
    skills: Optional[List[PydanticObjectId]] = None   # danh sách _id trong skills_taxonomy
    experience: Optional[List[ExperienceItem]] = None
    education: Optional[List[EducationItem]] = None


class ProfileResponse(BaseModel):
    user_id: PydanticObjectId
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    skills: List[PydanticObjectId] = []
    experience: List[dict] = []
    education: List[dict] = []
    cv_url: Optional[str] = None


class SkillResponse(BaseModel):
    id: PydanticObjectId
    name: str
    category: Optional[str] = None
