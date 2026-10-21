from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from beanie import PydanticObjectId

class JobCreateSchema(BaseModel):
    title: str
    description: str
    required_skills: List[PydanticObjectId] = Field(default_factory=list)
    level: Optional[str] = "MID"
    experience_required: int = 0
    salary: Optional[Dict[str, Any]] = None
    location: Optional[str] = None

class JobUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[PydanticObjectId]] = None
    level: Optional[str] = None
    experience_required: Optional[int] = None
    salary: Optional[Dict[str, Any]] = None
    location: Optional[str] = None

class JobStatusUpdateSchema(BaseModel):
    status: str  # "OPEN", "CLOSED", "HIDDEN"