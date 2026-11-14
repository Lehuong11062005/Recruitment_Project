"""Task 9.3: gửi email tự động qua SMTP.

`send_email` là hàm ĐỒNG BỘ, dùng với FastAPI BackgroundTasks:
    background_tasks.add_task(send_email, to_email, subject, text, html)
Starlette tự chạy hàm sync trong threadpool nên không chặn event loop.
Hàm KHÔNG BAO GIỜ raise: lỗi SMTP chỉ được ghi log, để việc đổi trạng thái đơn không bị hỏng theo.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from html import escape
from typing import Optional, Sequence

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_email_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM)


def _clean_header(value: str) -> str:
    # Chặn header injection: tiêu đề không được chứa xuống dòng
    return " ".join((value or "").split())


def render_html(title: str, paragraphs: Sequence[str], action_url: Optional[str] = None,
                action_label: str = "Xem chi tiết") -> str:
    body = "".join(f"<p style='margin:0 0 12px'>{escape(p)}</p>" for p in paragraphs)
    button = (
        f"<p style='margin:20px 0'><a href='{escape(action_url, quote=True)}' "
        "style='background:#2563eb;color:#fff;padding:10px 18px;border-radius:6px;"
        f"text-decoration:none'>{escape(action_label)}</a></p>"
        if action_url else ""
    )
    return (
        "<div style='font-family:Arial,sans-serif;font-size:14px;color:#1f2937;max-width:560px'>"
        f"<h2 style='color:#111827'>{escape(title)}</h2>{body}{button}"
        "<hr style='border:none;border-top:1px solid #e5e7eb;margin:24px 0'>"
        "<p style='font-size:12px;color:#6b7280'>Email tự động từ hệ thống Smart Recruitment, vui lòng không trả lời.</p>"
        "</div>"
    )


def send_email(to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
    """Gửi 1 email. Trả True nếu gửi thành công, False nếu bỏ qua/lỗi (không raise)."""
    if not to_email:
        return False
    if not is_email_configured():
        logger.info("SMTP chưa cấu hình, bỏ qua email tới %s: %s", to_email, subject)
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = _clean_header(subject)
        msg["From"] = _clean_header(settings.SMTP_FROM)
        msg["To"] = _clean_header(to_email)
        msg.set_content(body_text)
        if body_html:
            msg.add_alternative(body_html, subtype="html")

        timeout = settings.SMTP_TIMEOUT_SECONDS
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout,
                                  context=ssl.create_default_context()) as server:
                _login_and_send(server, msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls(context=ssl.create_default_context())
                _login_and_send(server, msg)
        logger.info("Đã gửi email tới %s: %s", to_email, subject)
        return True
    except Exception:  # noqa: BLE001 - email lỗi không được làm hỏng luồng chính
        logger.exception("Gửi email tới %s thất bại", to_email)
        return False


def _login_and_send(server: smtplib.SMTP, msg: EmailMessage) -> None:
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    server.send_message(msg)
