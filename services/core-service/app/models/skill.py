from datetime import datetime
from typing import Optional, List
from beanie import Document, Indexed
from pydantic import Field

class SkillsTaxonomy(Document):
    name: Indexed(str, unique=True)
    aliases: List[str] = []
    category: Optional[str] = None  # "Frontend", "Backend", "AI", "Soft Skill"
    level: List[str] = []           # ["Basic", "Intermediate", "Advanced"]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "skills_taxonomy"