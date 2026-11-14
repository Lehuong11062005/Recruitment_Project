"""Task 10.3 (UC-C8, UC-R7): nghiệp vụ chat dùng chung cho REST và WebSocket."""
from datetime import datetime, timezone
from typing import Dict, List, Optional

from beanie import PydanticObjectId
from beanie.operators import In, Or

from app.models.application import Application
from app.models.chat import Conversation, Message
from app.models.job import JobPosting
from app.models.user import User
from app.schemas.chat import (
    MAX_ATTACHMENTS,
    ConversationResponse,
    MessageResponse,
    PartyBrief,
)

LAST_MESSAGE_MAX = 200
ATTACHMENT_MAX_LENGTH = 500
ALLOWED_ATTACHMENT_PREFIXES = ("https://", "http://", "/uploads/")


class ChatError(Exception):
    """Lỗi nghiệp vụ chat; router đổi thành HTTPException, WebSocket đổi thành event lỗi/close code."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


# ---------- chuyển đổi ----------
def to_message_response(m: Message) -> MessageResponse:
    return MessageResponse(
        id=m.id, conversation_id=m.conversation_id, sender_id=m.sender_id,
        sender_role=m.sender_role, message_type=m.message_type, content=m.content,
        attachments=m.attachments, is_read=m.is_read, created_at=m.created_at,
    )


def is_participant(user: User, conv: Conversation) -> bool:
    return user.id in (conv.candidate_id, conv.recruiter_id)


# ---------- phòng chat ----------
async def get_or_create_conversation(
    user: User, job_id: PydanticObjectId, candidate_id: Optional[PydanticObjectId]
) -> Conversation:
    """Mỗi cặp (job_id, candidate_id) chỉ có 1 phòng chat; gọi lại sẽ trả phòng đã có."""
    job = await JobPosting.get(job_id)
    if job is None or job.deleted_at is not None:
        raise ChatError(404, "Không tìm thấy tin tuyển dụng")

    if user.user_type == "CANDIDATE":
        cand_id = user.id                       # ứng viên chỉ được tạo phòng cho chính mình
    elif user.user_type == "RECRUITER":
        if job.recruiter_id != user.id:
            raise ChatError(403, "Bạn không phải người đăng tin tuyển dụng này")
        if candidate_id is None:
            raise ChatError(422, "HR cần truyền candidate_id")
        candidate = await User.get(candidate_id)
        if candidate is None or candidate.user_type != "CANDIDATE" or candidate.deleted_at is not None:
            raise ChatError(404, "Không tìm thấy ứng viên")
        applied = await Application.find_one(
            Application.job_id == job_id, Application.candidate_id == candidate_id
        )
        if applied is None:
            raise ChatError(403, "Ứng viên chưa ứng tuyển vào tin này")
        cand_id = candidate_id
    else:
        raise ChatError(403, "Chỉ ứng viên hoặc nhà tuyển dụng mới dùng được chat")

    conv = await Conversation.find_one(
        Conversation.job_id == job_id, Conversation.candidate_id == cand_id
    )
    if conv is None:
        conv = Conversation(job_id=job_id, candidate_id=cand_id, recruiter_id=job.recruiter_id)
        await conv.insert()
    return conv


async def get_conversation_for_user(user: User, conversation_id: PydanticObjectId) -> Conversation:
    """Không phải thành viên -> 404 (không lộ việc phòng có tồn tại)."""
    conv = await Conversation.get(conversation_id)
    if conv is None or not is_participant(user, conv):
        raise ChatError(404, "Không tìm thấy cuộc hội thoại")
    return conv


async def list_conversations(user: User) -> List[ConversationResponse]:
    convs = await Conversation.find(
        Or(Conversation.candidate_id == user.id, Conversation.recruiter_id == user.id)
    ).sort("-updated_at").to_list()
    if not convs:
        return []

    other_ids = list({c.recruiter_id if c.candidate_id == user.id else c.candidate_id for c in convs})
    job_ids = list({c.job_id for c in convs if c.job_id})
    users: Dict[PydanticObjectId, User] = {u.id: u for u in await User.find(In(User.id, other_ids)).to_list()}
    jobs: Dict[PydanticObjectId, JobPosting] = (
        {j.id: j for j in await JobPosting.find(In(JobPosting.id, job_ids)).to_list()} if job_ids else {}
    )

    result = []
    for c in convs:
        other_id = c.recruiter_id if c.candidate_id == user.id else c.candidate_id
        other = users.get(other_id)
        unread = await Message.find(
            Message.conversation_id == c.id,
            Message.sender_id != user.id,
            Message.is_read == False,  # noqa: E712
        ).count()
        result.append(ConversationResponse(
            id=c.id, job_id=c.job_id, job_title=jobs[c.job_id].title if c.job_id in jobs else None,
            candidate_id=c.candidate_id, recruiter_id=c.recruiter_id,
            other_user=PartyBrief(id=other.id, full_name=other.full_name) if other else None,
            last_message=c.last_message, unread_count=unread, updated_at=c.updated_at,
        ))
    return result


# ---------- tin nhắn ----------
async def mark_read(conv: Conversation, user: User) -> None:
    """Đánh dấu đã đọc mọi tin của người kia trong phòng."""
    await Message.find(
        Message.conversation_id == conv.id,
        Message.sender_id != user.id,
        Message.is_read == False,  # noqa: E712
    ).update({"$set": {"is_read": True}})


async def list_messages(
    user: User, conversation_id: PydanticObjectId, limit: int = 50, before: Optional[datetime] = None
) -> List[MessageResponse]:
    """Lấy `limit` tin mới nhất (hoặc cũ hơn mốc `before`), trả về theo thứ tự cũ -> mới."""
    conv = await get_conversation_for_user(user, conversation_id)
    await mark_read(conv, user)

    conditions = [Message.conversation_id == conv.id]
    if before is not None:
        if before.tzinfo is not None:   # DB lưu datetime naive UTC
            before = before.astimezone(timezone.utc).replace(tzinfo=None)
        conditions.append(Message.created_at < before)
    items = await Message.find(*conditions).sort([("created_at", -1), ("_id", -1)]).limit(limit).to_list()
    items.reverse()
    return [to_message_response(m) for m in items]


def _preview(message_type: str, content: str) -> str:
    text = (content or "").strip()
    if text:
        return text[:LAST_MESSAGE_MAX]
    return "[Hình ảnh]" if message_type == "IMAGE" else "[Tệp đính kèm]"


async def save_message(
    conv: Conversation, user: User, message_type: str, content: str, attachments: List[str]
) -> Message:
    """Validate + lưu tin nhắn + cập nhật conversations.last_message/updated_at."""
    content = (content or "").strip()
    attachments = attachments or []
    if message_type == "TEXT":
        if not content:
            raise ChatError(422, "Nội dung tin nhắn không được để trống")
    elif not attachments:
        raise ChatError(422, "Tin nhắn FILE/IMAGE cần có ít nhất 1 attachment")
    if len(attachments) > MAX_ATTACHMENTS:
        raise ChatError(422, f"Tối đa {MAX_ATTACHMENTS} tệp đính kèm")
    for url in attachments:   # chặn link kiểu javascript: khi frontend render thành <a href>
        if len(url) > ATTACHMENT_MAX_LENGTH or not url.startswith(ALLOWED_ATTACHMENT_PREFIXES):
            raise ChatError(422, "Link đính kèm không hợp lệ")

    message = Message(
        conversation_id=conv.id, sender_id=user.id, sender_role=user.user_type or "",
        message_type=message_type, content=content, attachments=attachments, is_read=False,
    )
    await message.insert()
    await conv.set({"last_message": _preview(message_type, content), "updated_at": message.created_at})
    return message
