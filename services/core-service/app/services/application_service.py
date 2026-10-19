"""UC-C5: ứng viên nộp hồ sơ ứng tuyển.

Luồng: kiểm tra job -> chống nộp trùng -> lấy/lưu file CV PDF -> gọi AI Service
(parsed_text, điểm %, kỹ năng matched/missing) -> lưu vào collection applications
với pipeline_status = "APPLIED". AI lỗi thì vẫn lưu đơn (điểm = None) để ứng viên không mất đơn.
"""
import asyncio
import logging
import math
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

AI_PARSE_PATH = "/api/v1/ai/parse-cv"
AI_MATCH_PATH = "/api/v1/ai/match"
logger = logging.getLogger(__name__)


# ---------- hàm thuần, dễ test ----------
def _clamp_score(value: Any) -> Optional[float]:
    try:
        score = float(value)
        if not math.isfinite(score):
            return None
        return round(max(0.0, min(100.0, score)), 2)
    except (TypeError, ValueError, OverflowError):
        return None


def _ai_url(path: str) -> str:
    return settings.AI_URL.rstrip("/") + path


async def _call_ai_parse(filename: str, data: bytes) -> Optional[Dict[str, Any]]:
    """Parse a PDF with the AI Service; return None for unavailable or invalid responses."""
    url = _ai_url(AI_PARSE_PATH)
    try:
        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                url,
                files={"file": (filename, data, "application/pdf")},
            )
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            raise ValueError("response must be a JSON object")
        parsed_text = payload.get("parsed_text")
        skills = payload.get("skills")
        embedding = payload.get("embedding_vector")
        if (
            not isinstance(parsed_text, str)
            or not isinstance(skills, list)
            or any(not isinstance(skill, str) for skill in skills)
            or not isinstance(embedding, list)
            or any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in embedding)
        ):
            raise ValueError("response does not match ParseCVResponse")
        return payload
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("AI parse request failed (%s): %s", url, exc)
        return None


async def _call_ai_match(
    parsed_text: str,
    candidate_skills: List[str],
    job: JobPosting,
    required_names: List[str],
) -> Optional[Dict[str, Any]]:
    """Match parsed CV data against a job using the AI Service JSON contract."""
    url = _ai_url(AI_MATCH_PATH)
    body = {
        "cv_text": parsed_text,
        "jd_text": f"{job.title}\n{job.description}",
        "candidate_skills": candidate_skills,
        "required_skills": required_names,
        "candidate_experience_years": 0.0,
        "job_experience_required": float(job.experience_required or 0),
    }
    try:
        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=body)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            raise ValueError("response must be a JSON object")
        analysis = payload.get("ai_analysis")
        embedding = payload.get("embedding_vector")
        if (
            _clamp_score(payload.get("ai_match_score")) is None
            or not isinstance(payload.get("matching_version"), str)
            or not isinstance(embedding, list)
            or any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in embedding)
            or not isinstance(analysis, dict)
            or not isinstance(analysis.get("matched"), list)
            or not isinstance(analysis.get("missing"), list)
            or any(not isinstance(skill, str) for skill in analysis["matched"] + analysis["missing"])
            or not isinstance(analysis.get("score_breakdown"), dict)
            or any(
                not isinstance(value, (int, float)) or not math.isfinite(value)
                for value in analysis["score_breakdown"].values()
            )
            or not isinstance(analysis.get("recommendation"), str)
        ):
            raise ValueError("response does not match MatchingResponse")
        return payload
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("AI match request failed (%s): %s", url, exc)
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
async def apply_job(
    user: User,
    job_id: PydanticObjectId,
    file: Optional[UploadFile],
    submitted_required_names: Optional[List[str]] = None,
) -> ApplicationResponse:
    job = await JobPosting.get(job_id)
    if job is None or job.deleted_at is not None:
        raise CVError(404, "Không tìm thấy tin tuyển dụng")
    if job.status != "OPEN":
        raise CVError(400, "Tin tuyển dụng đã đóng, không thể ứng tuyển")
    if await Application.find_one(Application.job_id == job_id, Application.candidate_id == user.id):
        raise CVError(409, "Bạn đã ứng tuyển vị trí này rồi")

    # Từ điển kỹ năng: đổi tên kỹ năng AI trả về <-> _id trong skills_taxonomy
    skills = await SkillsTaxonomy.find_all().to_list()
    taxonomy = [{"id": s.id, "name": s.name, "aliases": s.aliases} for s in skills]
    id_to_name = {s.id: s.name for s in skills}
    required_ids = list(dict.fromkeys(job.required_skills))
    required_names = [id_to_name[i] for i in required_ids if i in id_to_name]
    if submitted_required_names is not None and {
        name.casefold() for name in submitted_required_names
    } != {name.casefold() for name in required_names}:
        raise CVError(422, "required_skills không khớp với kỹ năng bắt buộc của tin tuyển dụng")

    data, filename, path, cv_url = await _resolve_cv(user, file)
    parsed_text = None
    embedding = None
    score = None
    analysis = None
    ai_status = "FAILED"
    version = "v1.0"
    parsed = await _call_ai_parse(filename, data)
    if parsed is not None:
        parsed_text = parsed["parsed_text"]
        embedding = [float(value) for value in parsed["embedding_vector"]]
        ai = await _call_ai_match(parsed_text, parsed["skills"], job, required_names)
        if ai is not None:
            score = _clamp_score(ai["ai_match_score"])
            version = ai["matching_version"]
            match_embedding = ai["embedding_vector"]
            if match_embedding:
                embedding = [float(value) for value in match_embedding]

            ai_analysis = ai["ai_analysis"]
            matched_ids = [
                item["id"] for item in match_skill_names(ai_analysis["matched"], taxonomy)
            ]
            missing_ids = [
                item["id"] for item in match_skill_names(ai_analysis["missing"], taxonomy)
            ]
            analysis = AIAnalysis(
                matched=matched_ids,
                missing=missing_ids,
                score_breakdown={
                    key: float(value)
                    for key, value in ai_analysis["score_breakdown"].items()
                },
                recommendation=ai_analysis["recommendation"],
            )
            ai_status = "DONE"

    app = Application(
        job_id=job_id, candidate_id=user.id, cv_url=cv_url,
        parsed_text=parsed_text, embedding_vector=embedding,
        pipeline_status="APPLIED",
        status_history=[StatusHistory(status="APPLIED", changed_by=user.id)],
        ai_match_score=score, matching_version=version, ai_analysis=analysis,
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
