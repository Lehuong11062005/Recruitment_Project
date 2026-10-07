from datetime import datetime
from typing import Optional
from beanie import Document, PydanticObjectId
from pydantic import Field

class Notification(Document):
    user_id: PydanticObjectId             # FK tham chiếu users
    title: str
    content: str
    action_url: Optional[str] = None
    type: str = "SYSTEM"                  # "AI_RESULT", "APPLICATION_STATUS", "SYSTEM"
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expire_at: Optional[datetime] = None  # TTL Index

    class Settings:
        name = "notifications"
        indexes = [
            [("user_id", 1), ("is_read", 1)],
            [("expire_at", 1)],           # TTL index tự dọn bản ghi hết hạn
        ]