from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from beanie import PydanticObjectId

class CompanyCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, description="Tên doanh nghiệp")
    logo_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None

class CompanyUpdateSchema(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None

class CompanyResponseSchema(BaseModel):
    id: PydanticObjectId = Field(..., alias="_id")
    name: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    verification_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True