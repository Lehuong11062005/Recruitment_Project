from datetime import datetime
from typing import Optional, List
from beanie import Document, PydanticObjectId
from pydantic import Field

class Conversation(Document):
    job_id: Optional[PydanticObjectId] = None       # FK tham chiếu job_postings
    candidate_id: PydanticObjectId                 # FK tham chiếu users (Ứng viên)
    recruiter_id: PydanticObjectId                 # FK tham chiếu users (Nhà tuyển dụng)
    last_message: Optional[str] = None             # Text tin nhắn cuối để render list inbox nhanh
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "conversations"
        indexes = [
            [("candidate_id", 1)],
            [("recruiter_id", 1)],
        ]

class Message(Document):
    conversation_id: PydanticObjectId             # FK tham chiếu conversations
    sender_id: PydanticObjectId                   # FK tham chiếu users người gửi
    sender_role: str                              # "CANDIDATE" hoặc "RECRUITER"
    message_type: str = "TEXT"                    # "TEXT", "FILE", "IMAGE"
    content: str                                  # Nội dung văn bản
    attachments: List[str] = []                   # Danh sách link đính kèm nếu có
    is_read: bool = False                         # Trạng thái đã đọc
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "messages"
        indexes = [
            [("conversation_id", 1), ("created_at", -1)]  # Sort tin nhắn mới nhất
        ]