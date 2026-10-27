"""UC-C5: ứng viên nộp hồ sơ ứng tuyển.

Luồng: kiểm tra job -> chống nộp trùng -> lấy/lưu file CV PDF -> gọi AI Service
(parsed_text, điểm %, kỹ năng matched/missing) -> lưu vào collection applications
với pipeline_status = "APPLIED". AI lỗi thì vẫn lưu đơn (điểm = None) để ứng viên không mất đơn.
"""
import asyncio
import logging
import math
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from beanie import PydanticObjectId
from fastapi import UploadFile
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.storage import CV_DIR, UPLOAD_URL_PREFIX
from app.models.application import AIAnalysis, Application, StatusHistory
from app.models.company import Company
from app.models.job import JobPosting
from app.models.skill import SkillsTaxonomy
from app.models.user import User
from app.schemas.application import (
    AIAnalysisResponse,
    ApplicationDetailResponse,
    ApplicationResponse,
    CandidateBrief,
    SkillRef,
    StatusHistoryItem,
)
from app.services.cv_service import _url_to_path, read_limited
from app.services.cv_utils import CVError, map_skill_names, validate_pdf

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


def _candidate_experience_years(user: User) -> float:
    years_total = 0.0
    for item in user.profile.experience if user.profile else []:
        if not isinstance(item, dict):
            continue
        try:
            years = float(item.get("years") or 0)
        except (TypeError, ValueError):
            continue
        if math.isfinite(years) and years > 0:
            years_total += years
    return years_total


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
    candidate_experience_years: float = 0.0,
) -> Optional[Dict[str, Any]]:
    """Match parsed CV data against a job using the AI Service JSON contract."""
    url = _ai_url(AI_MATCH_PATH)
    body = {
        "cv_text": parsed_text,
        "jd_text": f"{job.title}\n{job.description}",
        "candidate_skills": candidate_skills,
        "required_skills": required_names,
        "candidate_experience_years": candidate_experience_years,
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


def _skill_maps(skills) -> tuple:
    """id -> {name, category} (để dựng SkillRef) và danh sách taxonomy (để quy đổi tên -> id)."""
    id_to_skill = {x.id: {"name": x.name, "category": x.category} for x in skills}
    taxonomy = [
        {"id": x.id, "name": x.name, "aliases": x.aliases, "category": x.category}
        for x in skills
    ]
    return id_to_skill, taxonomy


def _skill_ref(skill_id, id_to_skill: Dict[Any, Dict[str, Any]]) -> SkillRef:
    info = id_to_skill.get(skill_id) or {}
    return SkillRef(id=skill_id, name=info.get("name", ""), category=info.get("category"))


def _to_response(
    app: Application, ai_status: str, id_to_skill: Dict[Any, Dict[str, Any]]
) -> ApplicationResponse:
    analysis = None
    if app.ai_analysis is not None:
        a = app.ai_analysis
        analysis = AIAnalysisResponse(
            matched=[_skill_ref(i, id_to_skill) for i in a.matched],
            missing=[_skill_ref(i, id_to_skill) for i in a.missing],
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


async def _application_response(app: Application) -> ApplicationResponse:
    skills = await SkillsTaxonomy.find_all().to_list()
    id_to_skill, _ = _skill_maps(skills)
    response = _to_response(
        app,
        "DONE" if app.ai_match_score is not None else "FAILED",
        id_to_skill,
    )
    job = await JobPosting.get(app.job_id)
    if job is not None:
        company = await Company.get(job.company_id)
        response.job_title = job.title
        response.company_name = company.name if company else None
    return response


async def list_candidate_applications(user: User) -> List[ApplicationResponse]:
    applications = await Application.find(
        Application.candidate_id == user.id
    ).sort("-applied_at").to_list()
    return [await _application_response(app) for app in applications]


async def get_candidate_application(
    user: User,
    application_id: PydanticObjectId,
) -> ApplicationResponse:
    app = await Application.get(application_id)
    if app is None or app.candidate_id != user.id:
        raise CVError(404, "Không tìm thấy hồ sơ ứng tuyển")
    return await _application_response(app)


async def _get_authorized_application(
    user: User, application_id: PydanticObjectId
) -> Application:
    """Chỉ ứng viên chủ đơn, hoặc nhà tuyển dụng cùng công ty với tin tuyển dụng, được xem.

    Mọi trường hợp không đủ quyền đều trả 404 (không lộ việc đơn có tồn tại hay không).
    """
    not_found = CVError(404, "Không tìm thấy hồ sơ ứng tuyển")
    app = await Application.get(application_id)
    if app is None:
        raise not_found
    if user.user_type == "CANDIDATE":
        if app.candidate_id != user.id:
            raise not_found
    elif user.user_type == "RECRUITER":
        job = await JobPosting.get(app.job_id)
        if job is None or user.company_id is None or job.company_id != user.company_id:
            raise not_found
    else:
        raise not_found
    return app


async def get_cv_file_path(user: User, application_id: PydanticObjectId) -> Path:
    """Task 8.3: đường dẫn file PDF gốc của đơn sau khi kiểm tra quyền."""
    app = await _get_authorized_application(user, application_id)
    path = _url_to_path(app.candidate_id, app.cv_url)   # đã chặn path traversal
    if path is None or not path.exists():
        raise CVError(404, "Không tìm thấy file CV")
    return path


async def get_application_detail(
    user: User, application_id: PydanticObjectId
) -> ApplicationDetailResponse:
    """GET /applications/{id}: dùng chung cho ứng viên chủ đơn và HR nhận đơn."""
    app = await _get_authorized_application(user, application_id)
    base = await _application_response(app)

    candidate = await User.get(app.candidate_id)
    if candidate is None:
        raise CVError(404, "Không tìm thấy hồ sơ ứng viên")
    skills = await SkillsTaxonomy.find_all().to_list()
    id_to_skill, _ = _skill_maps(skills)
    profile = candidate.profile
    brief = CandidateBrief(
        id=candidate.id,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone or (profile.phone if profile else None),
        summary=profile.summary if profile else None,
        location=profile.location if profile else None,
        skills=[_skill_ref(i, id_to_skill) for i in (profile.skills if profile else [])],
        experience=profile.experience if profile else [],
        education=profile.education if profile else [],
    )
    is_hr = user.user_type == "RECRUITER"
    return ApplicationDetailResponse(
        **base.model_dump(),
        candidate=brief,
        cv_preview_url=f"/api/v1/applications/{app.id}/cv",
        cv_parsed_text=app.parsed_text,
        recruiter_note=app.recruiter_note if is_hr else None,
        status_history=[StatusHistoryItem(status=h.status, time=h.time) for h in app.status_history],
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
    id_to_skill, taxonomy = _skill_maps(skills)
    id_to_name = {i: v["name"] for i, v in id_to_skill.items()}
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
        ai = await _call_ai_match(
            parsed_text,
            parsed["skills"],
            job,
            required_names,
            _candidate_experience_years(user),
        )
        if ai is not None:
            score = _clamp_score(ai["ai_match_score"])
            version = ai["matching_version"]
            match_embedding = ai["embedding_vector"]
            if match_embedding:
                embedding = [float(value) for value in match_embedding]

            ai_analysis = ai["ai_analysis"]
            matched, unmapped_m = map_skill_names(ai_analysis["matched"], taxonomy)
            missing, unmapped_x = map_skill_names(ai_analysis["missing"], taxonomy)
            if unmapped_m or unmapped_x:
                # gợi ý bổ sung alias vào skill_taxonomy.json
                logger.warning(
                    "Skill AI trả về nhưng không có trong taxonomy: %s", unmapped_m + unmapped_x
                )
            matched_ids = [m["id"] for m in matched]
            matched_set = set(matched_ids)
            missing_ids = [m["id"] for m in missing if m["id"] not in matched_set]
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
    return _to_response(app, ai_status, id_to_skill)
