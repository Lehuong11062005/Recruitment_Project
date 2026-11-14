from typing import List, Literal, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from app.schemas.notification import UTCDatetime

MessageType = Literal["TEXT", "FILE", "IMAGE"]

MAX_CONTENT_LENGTH = 2000
MAX_ATTACHMENTS = 5


class ConversationCreate(BaseModel):
    """POST /api/v1/conversations.

    - Ứng viên gọi: chỉ cần job_id (HR = người đăng tin).
    - HR gọi: cần job_id + candidate_id (ứng viên đã nộp đơn vào tin đó).
    """
    job_id: PydanticObjectId
    candidate_id: Optional[PydanticObjectId] = None


class PartyBrief(BaseModel):
    id: PydanticObjectId
    full_name: str


class ConversationResponse(BaseModel):
    id: PydanticObjectId
    job_id: Optional[PydanticObjectId] = None
    job_title: Optional[str] = None
    candidate_id: PydanticObjectId
    recruiter_id: PydanticObjectId
    other_user: Optional[PartyBrief] = None   # người ở đầu bên kia (so với user đang đăng nhập)
    last_message: Optional[str] = None
    unread_count: int = 0
    updated_at: UTCDatetime


class MessageResponse(BaseModel):
    id: PydanticObjectId
    conversation_id: PydanticObjectId
    sender_id: PydanticObjectId
    sender_role: str
    message_type: str
    content: str
    attachments: List[str] = []
    is_read: bool
    created_at: UTCDatetime


class WSIncomingMessage(BaseModel):
    """Payload client gửi lên qua WebSocket (event = "message")."""
    message_type: MessageType = "TEXT"
    content: str = Field(default="", max_length=MAX_CONTENT_LENGTH)
    attachments: List[str] = Field(default_factory=list, max_length=MAX_ATTACHMENTS)
