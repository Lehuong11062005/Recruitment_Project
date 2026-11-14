"""Task 9.3: 2 API thông báo cho Frontend (gắn prefix /api/v1/notifications ở main.py)."""
from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationResponse

router = APIRouter()


def _to_response(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=n.id, user_id=n.user_id, title=n.title, content=n.content, type=n.type,
        action_url=n.action_url, is_read=n.is_read, created_at=n.created_at,
    )


@router.get("", response_model=List[NotificationResponse],
            summary="Danh sách thông báo của tôi (mới nhất trước)")
async def list_notifications(
    unread_only: bool = Query(False, description="Chỉ lấy thông báo chưa đọc"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
):
    conditions = [Notification.user_id == user.id]
    if unread_only:
        conditions.append(Notification.is_read == False)  # noqa: E712
    items = await Notification.find(*conditions).sort("-created_at").skip(skip).limit(limit).to_list()
    return [_to_response(n) for n in items]


@router.patch("/{notification_id}/read", response_model=NotificationResponse,
              summary="Đánh dấu 1 thông báo là đã đọc")
async def mark_notification_read(notification_id: str, user: User = Depends(get_current_user)):
    try:
        oid = PydanticObjectId(notification_id)
    except Exception:
        raise HTTPException(422, "notification_id không hợp lệ")
    notification = await Notification.get(oid)
    # Không phải của mình -> 404 (không lộ việc thông báo có tồn tại)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(404, "Không tìm thấy thông báo")
    if not notification.is_read:
        notification.is_read = True
        await notification.save()
    return _to_response(notification)
