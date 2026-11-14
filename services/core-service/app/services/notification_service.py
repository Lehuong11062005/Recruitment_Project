"""Task 9.3: tạo thông báo trong DB + gửi email khi trạng thái đơn ứng tuyển thay đổi.

Cách dùng cho Mạnh (trong API đổi trạng thái / gửi lịch phỏng vấn):

    from fastapi import BackgroundTasks
    from app.services import notification_service

    @router.patch("/{application_id}/status")
    async def update_status(..., background_tasks: BackgroundTasks, ...):
        ...  # đổi pipeline_status, ghi status_history, save()
        await notification_service.notify_application_status(app, background_tasks)

    # Khi HR gửi lịch phỏng vấn (đã lưu app.interview_schedule):
        await notification_service.notify_interview_schedule(app, background_tasks)

Các hàm notify_* không bao giờ raise: lỗi thông báo/email chỉ ghi log.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId
from fastapi import BackgroundTasks

from app.core.config import settings
from app.models.application import Application
from app.models.company import Company
from app.models.job import JobPosting
from app.models.notification import Notification
from app.models.user import User
from app.services import email_service

logger = logging.getLogger(__name__)

NOTIFICATION_TYPE_APPLICATION_STATUS = "APPLICATION_STATUS"

STATUS_LABELS = {
    "APPLIED": "Đã nộp hồ sơ",
    "SCREENING": "Đang sơ loại",
    "INTERVIEW": "Hẹn phỏng vấn",
    "HIRED": "Trúng tuyển",
    "REJECTED": "Từ chối",
}


async def create_notification(
    user_id: PydanticObjectId,
    title: str,
    content: str,
    *,
    type: str = NOTIFICATION_TYPE_APPLICATION_STATUS,
    action_url: Optional[str] = None,
) -> Notification:
    """Ghi 1 bản ghi vào collection notifications (is_read = False)."""
    notification = Notification(
        user_id=user_id, title=title, content=content, type=type,
        action_url=action_url, is_read=False,
    )
    await notification.insert()
    return notification


# ---------- helpers ----------
async def _load_context(application: Application):
    candidate = await User.get(application.candidate_id)
    job = await JobPosting.get(application.job_id)
    company = await Company.get(job.company_id) if job is not None else None
    return candidate, job, company


def _format_when(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.strftime("%H:%M ngày %d/%m/%Y")
    return str(value)


def _schedule_lines(schedule: Optional[Dict[str, Any]]) -> List[str]:
    """Đọc lịch phỏng vấn linh hoạt theo nhiều tên key (chốt key chính thức với Mạnh)."""
    if not isinstance(schedule, dict):
        return []
    pick = lambda *keys: next((schedule[k] for k in keys if schedule.get(k)), None)  # noqa: E731
    lines = []
    when = _format_when(pick("time", "scheduled_at", "datetime", "date"))
    if when:
        lines.append(f"Thời gian: {when}")
    if pick("location", "address"):
        lines.append(f"Địa điểm: {pick('location', 'address')}")
    if pick("meeting_link", "link", "url"):
        lines.append(f"Link phỏng vấn: {pick('meeting_link', 'link', 'url')}")
    if pick("note", "notes"):
        lines.append(f"Ghi chú: {pick('note', 'notes')}")
    return lines


def _status_message(status: str, job_title: str, company_name: str) -> str:
    where = f"{job_title} tại {company_name}" if company_name else job_title
    return {
        "SCREENING": f"Hồ sơ của bạn cho vị trí {where} đang được nhà tuyển dụng xem xét.",
        "INTERVIEW": f"Chúc mừng! Bạn được mời phỏng vấn cho vị trí {where}.",
        "HIRED": f"Chúc mừng! Bạn đã trúng tuyển vị trí {where}.",
        "REJECTED": f"Rất tiếc, hồ sơ của bạn cho vị trí {where} chưa phù hợp ở thời điểm này.",
    }.get(status, f"Trạng thái đơn ứng tuyển vị trí {where} đã chuyển sang: {STATUS_LABELS.get(status, status)}.")


async def _notify_candidate(
    application: Application,
    background_tasks: Optional[BackgroundTasks],
    *,
    title: str,
    content: str,
    extra_lines: Optional[List[str]] = None,
    candidate: Optional[User] = None,
) -> Optional[Notification]:
    action_path = f"/candidate/applications/{application.id}"
    lines = [content, *(extra_lines or [])]
    notification = await create_notification(
        application.candidate_id, title, "\n".join(lines), action_url=action_path,
    )
    if candidate is not None and candidate.email:
        link = settings.FRONTEND_URL.rstrip("/") + action_path
        text = "\n".join([f"Xin chào {candidate.full_name},", "", *lines, "", f"Xem chi tiết: {link}"])
        html = email_service.render_html(title, [f"Xin chào {candidate.full_name},", *lines], link)
        if background_tasks is not None:
            background_tasks.add_task(email_service.send_email, candidate.email, title, text, html)
        else:  # không có BackgroundTasks (vd. gọi từ script): gửi trực tiếp, vẫn không raise
            email_service.send_email(candidate.email, title, text, html)
    return notification


# ---------- API nội bộ cho các router khác gọi ----------
async def notify_application_status(
    application: Application,
    background_tasks: Optional[BackgroundTasks] = None,
    new_status: Optional[str] = None,
) -> Optional[Notification]:
    """Báo cho ứng viên khi HR đổi trạng thái đơn. new_status mặc định = application.pipeline_status."""
    try:
        status = new_status or application.pipeline_status
        candidate, job, company = await _load_context(application)
        if candidate is None or job is None:
            logger.warning("Bỏ qua thông báo: thiếu ứng viên/tin tuyển dụng cho đơn %s", application.id)
            return None
        title = f"Cập nhật đơn ứng tuyển: {STATUS_LABELS.get(status, status)}"
        extra = _schedule_lines(application.interview_schedule) if status == "INTERVIEW" else []
        return await _notify_candidate(
            application, background_tasks, title=title,
            content=_status_message(status, job.title, company.name if company else ""),
            extra_lines=extra, candidate=candidate,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Tạo thông báo đổi trạng thái thất bại (đơn %s)", getattr(application, "id", None))
        return None


async def notify_interview_schedule(
    application: Application,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Optional[Notification]:
    """Báo cho ứng viên khi HR gửi/cập nhật lịch phỏng vấn (đọc từ application.interview_schedule)."""
    try:
        candidate, job, company = await _load_context(application)
        if candidate is None or job is None:
            logger.warning("Bỏ qua thông báo: thiếu ứng viên/tin tuyển dụng cho đơn %s", application.id)
            return None
        where = f"{job.title} tại {company.name}" if company else job.title
        return await _notify_candidate(
            application, background_tasks,
            title="Lịch phỏng vấn mới",
            content=f"Nhà tuyển dụng đã gửi lịch phỏng vấn cho vị trí {where}.",
            extra_lines=_schedule_lines(application.interview_schedule),
            candidate=candidate,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Tạo thông báo lịch phỏng vấn thất bại (đơn %s)", getattr(application, "id", None))
        return None
