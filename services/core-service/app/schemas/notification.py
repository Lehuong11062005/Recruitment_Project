from datetime import datetime, timezone
from typing import Annotated, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, PlainSerializer


def _iso_utc(value: datetime) -> str:
    """Mongo trả datetime naive (UTC). Thêm hậu tố Z để trình duyệt không hiểu nhầm là giờ local."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UTCDatetime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str, when_used="json")]


class NotificationResponse(BaseModel):
    id: PydanticObjectId
    user_id: PydanticObjectId
    title: str
    content: str
    type: str
    action_url: Optional[str] = None
    is_read: bool
    created_at: UTCDatetime
