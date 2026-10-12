"""UC-C3: lưu file CV PDF của ứng viên và nhờ AI Service gợi ý kỹ năng."""
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import httpx
from fastapi import UploadFile

from app.core.config import settings
from app.core.storage import CV_DIR, UPLOAD_URL_PREFIX
from app.models.skill import SkillsTaxonomy
from app.models.user import CandidateProfile, User
from app.schemas.user import CVExtraction, CVUploadResponse, SuggestedSkill
from app.services.cv_utils import (
    CVError,
    match_skill_names,
    parse_ai_skill_names,
    validate_pdf,
)

AI_PARSE_PATH = "/api/v1/ai/parse-cv"   # API AI Service cần cung cấp (UC-AI1)
_CHUNK = 1024 * 1024


async def read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Đọc từng khúc 1 MB, dừng ngay khi vượt giới hạn để không nạp file khổng lồ vào RAM."""
    buf = bytearray()
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise CVError(413, f"File quá lớn, tối đa {max_bytes // (1024 * 1024)} MB")
    return bytes(buf)


def _url_to_path(user_id, cv_url: Optional[str]) -> Optional[Path]:
    """Đổi cv_url cũ thành đường dẫn file, chỉ khi nó nằm đúng thư mục CV của user này."""
    prefix = f"{UPLOAD_URL_PREFIX}/cvs/{user_id}/"
    if not cv_url or not cv_url.startswith(prefix):
        return None
    path = (CV_DIR / str(user_id) / cv_url[len(prefix):]).resolve()
    if (CV_DIR / str(user_id)).resolve() not in path.parents:
        return None
    return path


async def _extract_with_ai(filename: str, data: bytes) -> CVExtraction:
    """Gọi AI Service; lỗi gì cũng không làm hỏng việc upload."""
    if not settings.AI_URL:
        return CVExtraction(status="SKIPPED", message="Chưa cấu hình AI_URL nên bỏ qua bước phân tích CV")
    url = settings.AI_URL.rstrip("/") + AI_PARSE_PATH
    try:
        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, files={"file": (filename, data, "application/pdf")})
        resp.raise_for_status()
        names = parse_ai_skill_names(resp.json())
    except Exception:
        return CVExtraction(status="FAILED", message="Không phân tích được CV lúc này, bạn có thể nhập kỹ năng thủ công")

    skills = await SkillsTaxonomy.find_all().to_list()
    matched = match_skill_names(
        names, [{"id": s.id, "name": s.name, "aliases": s.aliases} for s in skills]
    )
    return CVExtraction(
        status="DONE",
        suggested_skills=[SuggestedSkill(id=m["id"], name=m["name"]) for m in matched],
    )


async def upload_cv(user: User, file: UploadFile) -> CVUploadResponse:
    filename = file.filename or ""
    data = await read_limited(file, settings.CV_MAX_SIZE_MB * 1024 * 1024)
    validate_pdf(filename, data, settings.CV_MAX_SIZE_MB * 1024 * 1024)

    # 1. Lưu file mới
    user_dir = CV_DIR / str(user.id)
    new_name = f"{uuid.uuid4().hex}.pdf"
    new_path = user_dir / new_name

    def _write() -> None:
        user_dir.mkdir(parents=True, exist_ok=True)
        new_path.write_bytes(data)

    await asyncio.to_thread(_write)

    # 2. Cập nhật users.profile.cv_url; hỏng DB thì xóa file vừa lưu để khỏi mồ côi
    if user.profile is None:
        user.profile = CandidateProfile()
    old_path = _url_to_path(user.id, user.profile.cv_url)
    new_url = f"{UPLOAD_URL_PREFIX}/cvs/{user.id}/{new_name}"
    user.profile.cv_url = new_url
    user.updated_at = datetime.utcnow()
    try:
        await user.save()
    except Exception:
        new_path.unlink(missing_ok=True)
        raise

    # 3. Xóa CV cũ (nếu có), rồi nhờ AI gợi ý kỹ năng
    if old_path is not None:
        old_path.unlink(missing_ok=True)
    extraction = await _extract_with_ai(filename, data)

    return CVUploadResponse(cv_url=new_url, filename=filename, size=len(data), extraction=extraction)
