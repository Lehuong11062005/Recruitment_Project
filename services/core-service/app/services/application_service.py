"""UC-C5: ứng viên nộp hồ sơ ứng tuyển.

Luồng: kiểm tra job -> chống nộp trùng -> lấy/lưu file CV PDF -> gọi AI Service
(parsed_text, điểm %, kỹ năng matched/missing) -> lưu vào collection applications
với pipeline_status = "APPLIED". AI lỗi thì vẫn lưu đơn (điểm = None) để ứng viên không mất đơn.
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

import httpx
from beanie import PydanticObjectId
from fastapi import UploadFile
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.storage import CV_DIR, UPLOAD_URL_PREFIX
from app.models.application import AIAnalysis, Application, StatusHistory
from app.models.job import JobPosting
from app.models.skill import SkillsTaxonomy
from app.models.user import User
from app.schemas.application import AIAnalysisResponse, ApplicationResponse, SkillRef
from app.services.cv_service import _url_to_path, read_limited
from app.services.cv_utils import CVError, match_skill_names, validate_pdf

AI_MATCH_PATH = "/api/v1/ai/match-cv"   # API AI Service (Hưởng) cần cung cấp - xem hợp đồng trong hướng dẫn


# ---------- hàm thuần, dễ test ----------
def _clamp_score(value: Any) -> Optional[float]:
    try:
        return round(max(0.0, min(100.0, float(value))), 2)
    except (TypeError, ValueError):
        return None


def _names(items: Any) -> List[str]:
    out: List[str] = []
    for it in items or []:
        if isinstance(it, str) and it.strip():
            out.append(it.strip())
        elif isinstance(it, dict) and isinstance(it.get("name"), str) and it["name"].strip():
            out.append(it["name"].strip())
    return out


async def _call_ai_match(filename: str, data: bytes, job: JobPosting,
                         required_names: List[str]) -> Optional[Dict[str, Any]]:
    """Trả về JSON AI hoặc None (chưa cấu hình / lỗi mạng / AI trả sai)."""
    if not settings.AI_URL:
        return None
    url = settings.AI_URL.rstrip("/") + AI_MATCH_PATH
    form = {"jd_text": f"{job.title}\n{job.description}", "required_skills": json.dumps(required_names)}
    try:
        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, data=form, files={"file": (filename, data, "application/pdf")})
        resp.raise_for_status()
        payload = resp.json()
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _save_file(user_id: PydanticObjectId, data: bytes) -> tuple:
    user_dir = CV_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.pdf"
    path = user_dir / name
    path.write_bytes(data)
    return path, f"{UPLOAD_URL_PREFIX}/cvs/{user_id}/{name}"


async def _resolve_cv(user: User, file: Optional[UploadFile]) -> tuple:
    """Trả về (bytes, filename, path đã lưu, cv_url). Mỗi đơn có bản sao CV riêng,
    để sau này ứng viên thay CV trong hồ sơ cũng không làm hỏng đơn cũ."""
    max_bytes = settings.CV_MAX_SIZE_MB * 1024 * 1024
    if file is not None and (file.filename or ""):
        filename = file.filename
        data = await read_limited(file, max_bytes)
        validate_pdf(filename, data, max_bytes)
    else:
        src = _url_to_path(user.id, user.profile.cv_url if user.profile else None)
        if src is None or not src.exists():
            raise CVError(400, "Bạn chưa có CV trong hồ sơ, hãy đính kèm file PDF khi nộp đơn")
        data = await asyncio.to_thread(src.read_bytes)
        filename = src.name
        validate_pdf(filename, data, max_bytes)
    path, url = await asyncio.to_thread(_save_file, user.id, data)
    return data, filename, path, url


def _to_response(app: Application, ai_status: str, id_to_name: Dict[Any, str]) -> ApplicationResponse:
    analysis = None
    if app.ai_analysis is not None:
        a = app.ai_analysis
        analysis = AIAnalysisResponse(
            matched=[SkillRef(id=i, name=id_to_name.get(i, "")) for i in a.matched],
            missing=[SkillRef(id=i, name=id_to_name.get(i, "")) for i in a.missing],
            score_breakdown=a.score_breakdown,
            recommendation=a.recommendation,
        )
    return ApplicationResponse(
        id=app.id, job_id=app.job_id, candidate_id=app.candidate_id, cv_url=app.cv_url,
        pipeline_status=app.pipeline_status, ai_status=ai_status,
        ai_match_score=app.ai_match_score, matching_version=app.matching_version,
        ai_analysis=analysis,
        parsed_text_preview=(app.parsed_text or "")[:300] or None,
        applied_at=app.applied_at,
    )


# ---------- nghiệp vụ chính ----------
async def apply_job(user: User, job_id: PydanticObjectId, file: Optional[UploadFile]) -> ApplicationResponse:
    job = await JobPosting.get(job_id)
    if job is None or job.deleted_at is not None:
        raise CVError(404, "Không tìm thấy tin tuyển dụng")
    if job.status != "OPEN":
        raise CVError(400, "Tin tuyển dụng đã đóng, không thể ứng tuyển")
    if await Application.find_one(Application.job_id == job_id, Application.candidate_id == user.id):
        raise CVError(409, "Bạn đã ứng tuyển vị trí này rồi")

    data, filename, path, cv_url = await _resolve_cv(user, file)

    # Từ điển kỹ năng: đổi tên kỹ năng AI trả về <-> _id trong skills_taxonomy
    skills = await SkillsTaxonomy.find_all().to_list()
    taxonomy = [{"id": s.id, "name": s.name, "aliases": s.aliases} for s in skills]
    id_to_name = {s.id: s.name for s in skills}
    required_ids = list(dict.fromkeys(job.required_skills))
    required_names = [id_to_name[i] for i in required_ids if i in id_to_name]

    ai = await _call_ai_match(filename, data, job, required_names)

    score = parsed_text = embedding = analysis = None
    ai_status = "SKIPPED" if not settings.AI_URL else "FAILED"
    version = None
    if ai is not None:
        score = _clamp_score(ai.get("match_score"))
        if score is not None:
            ai_status = "DONE"
            parsed_text = ai.get("parsed_text") if isinstance(ai.get("parsed_text"), str) else None
            emb = ai.get("embedding")
            embedding = [float(x) for x in emb] if isinstance(emb, list) else None
            version = ai.get("model_version") or "v1.0"
            matched_ids = [m["id"] for m in match_skill_names(_names(ai.get("matched_skills")), taxonomy)]
            missing_ids = [m["id"] for m in match_skill_names(_names(ai.get("missing_skills")), taxonomy)]
            if not missing_ids:   # AI không trả missing -> tự suy ra từ JD
                missing_ids = [i for i in required_ids if i not in set(matched_ids)]
            breakdown = ai.get("score_breakdown")
            analysis = AIAnalysis(
                matched=matched_ids, missing=missing_ids,
                score_breakdown={k: float(v) for k, v in breakdown.items()
                                 if isinstance(v, (int, float))} if isinstance(breakdown, dict) else None,
                recommendation=ai.get("recommendation") if isinstance(ai.get("recommendation"), str) else None,
            )

    app = Application(
        job_id=job_id, candidate_id=user.id, cv_url=cv_url,
        parsed_text=parsed_text, embedding_vector=embedding,
        pipeline_status="APPLIED",
        status_history=[StatusHistory(status="APPLIED", changed_by=user.id)],
        ai_match_score=score, matching_version=version or "v1.0", ai_analysis=analysis,
    )
    try:
        await app.insert()
    except DuplicateKeyError:           # 2 request nộp cùng lúc (unique index job_id + candidate_id)
        path.unlink(missing_ok=True)
        raise CVError(409, "Bạn đã ứng tuyển vị trí này rồi")
    except Exception:
        path.unlink(missing_ok=True)    # lỗi DB thì không để lại file mồ côi
        raise

    await job.update({"$inc": {"applications_count": 1}})
    return _to_response(app, ai_status, id_to_name)
