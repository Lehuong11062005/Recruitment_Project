from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field

class Company(Document):
    name: Indexed(str, unique=True)
    logo_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    verification_status: str = "PENDING"  # "PENDING", "VERIFIED", "REJECTED"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    class Settings:
        name = "companies"