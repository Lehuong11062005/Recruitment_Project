"""UC-C5: ứng viên nộp hồ sơ ứng tuyển.

Luồng: kiểm tra job -> chống nộp trùng -> lấy/lưu file CV PDF -> gọi AI Service
(parsed_text, điểm %, kỹ năng matched/missing) -> lưu vào collection applications
với pipeline_status = "APPLIED". AI lỗi thì vẫn lưu đơn (điểm = None) để ứng viên không mất đơn.
"""
import asyncio
import logging
import math
import uuid
from datetime import datetime
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from bson.errors import InvalidId
from beanie import PydanticObjectId
from fastapi import UploadFile
from fastapi import BackgroundTasks
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.storage import CV_DIR, UPLOAD_URL_PREFIX
from app.models.application import AIAnalysis, Application, StatusHistory
from app.models.company import Company
from app.models.job import JobPosting, MatchingWeights
from app.models.skill import SkillsTaxonomy
from app.models.user import User
from app.schemas.job import MatchingWeightsSchema, resolve_matching_weights
from app.services.job_service import JobService
from app.schemas.application import (
    AIAnalysisResponse,
    ApplicationCompanyBrief,
    ApplicationDetailResponse,
    ApplicationJobBrief,
    ApplicationResponse,
    ApplicationStatusResponse,
    ApplicationStatusUpdate,
    CandidateBrief,
    RankedApplicationItem,
    RankedSkillItem,
    SkillRef,
    StatusHistoryItem,
)
from app.services.cv_service import _url_to_path, read_limited
from app.services import notification_service
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


def _to_weights_schema(raw: Any) -> Optional[MatchingWeightsSchema]:
    """Chuyển snapshot lưu trong DB sang schema trả về; giữ nguyên None cho bản ghi cũ."""
    if raw is None:
        return None
    if isinstance(raw, MatchingWeightsSchema):
        return raw
    data = raw.model_dump() if hasattr(raw, "model_dump") else raw
    if not isinstance(data, dict) or not data:
        return None
    try:
        return MatchingWeightsSchema.model_validate(data)
    except Exception:
        return None


def _extract_weights_snapshot(
    job: Any,
    ai_payload: Optional[Dict[str, Any]] = None,
) -> MatchingWeights:
    """Lấy snapshot trọng số từ phản hồi AI Service, hoặc fallback từ cấu hình JobPosting."""
    if isinstance(ai_payload, dict):
        raw_snap = ai_payload.get("matching_weights_snapshot")
        checked = _to_weights_schema(raw_snap)
        if checked is not None:
            return MatchingWeights(**checked.model_dump())
    return MatchingWeights(**JobService.get_job_matching_weights(job))


async def _call_ai_match(
    parsed_text: str,
    candidate_skills: List[str],
    job: JobPosting,
    required_names: List[str],
    candidate_experience_years: float = 0.0,
) -> Optional[Dict[str, Any]]:
    """Match parsed CV data against a job using the AI Service JSON contract."""
    url = _ai_url(AI_MATCH_PATH)
    weights_dict = JobService.get_job_matching_weights(job)
    body = {
        "cv_text": parsed_text,
        "jd_text": f"{job.title}\n{job.description}",
        "candidate_skills": candidate_skills,
        "required_skills": required_names,
        "candidate_experience_years": candidate_experience_years,
        "job_experience_required": float(job.experience_required or 0),
        "matching_weights": weights_dict,
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
            matched_skills=[_skill_ref(i, id_to_skill) for i in a.matched],
            missing_skills=[_skill_ref(i, id_to_skill) for i in a.missing],
            score_breakdown=a.score_breakdown,
            recommendation=a.recommendation,
        )
    raw_status = getattr(app, "ai_status", None) or ai_status
    normalized_status = "DONE" if raw_status == "COMPLETED" else raw_status
    history = [
        StatusHistoryItem(
            status=h.status,
            time=h.time,
            changed_by=getattr(h, "changed_by", None),
        )
        for h in (getattr(app, "status_history", None) or [])
    ]
    return ApplicationResponse(
        id=app.id,
        job_id=app.job_id,
        candidate_id=app.candidate_id,
        cv_url=app.cv_url,
        pipeline_status=app.pipeline_status,
        status_history=history,
        interview_schedule=getattr(app, "interview_schedule", None),
        ai_status=normalized_status,
        ai_match_score=app.ai_match_score,
        matching_version=app.matching_version,
        score_breakdown=analysis.score_breakdown if analysis is not None else None,
        matching_weights_snapshot=_to_weights_schema(
            getattr(app, "matching_weights_snapshot", None)
        ),
        ai_analysis=analysis,
        ai_analyzed_at=getattr(app, "ai_analyzed_at", None),
        parsed_text_preview=(app.parsed_text or "")[:300] or None,
        applied_at=app.applied_at,
        updated_at=getattr(app, "updated_at", None),
    )


def _attach_job_and_company(
    response: ApplicationResponse,
    job: Optional[JobPosting],
    company: Optional[Company],
) -> ApplicationResponse:
    if job is not None:
        job_deleted = getattr(job, "deleted_at", None) is not None
        response.job_title = job.title
        response.job = ApplicationJobBrief(
            id=job.id,
            title=job.title,
            location=getattr(job, "location", None),
            level=getattr(job, "level", None),
            salary=getattr(job, "salary", None),
            status="DELETED" if job_deleted else getattr(job, "status", None),
            is_deleted=job_deleted,
        )
    if company is not None:
        company_deleted = getattr(company, "deleted_at", None) is not None
        response.company_name = company.name
        response.company = ApplicationCompanyBrief(
            id=company.id,
            name=company.name,
            logo_url=getattr(company, "logo_url", None),
            industry=getattr(company, "industry", None),
            address=getattr(company, "address", None),
            verification_status=getattr(company, "verification_status", None),
            is_deleted=company_deleted,
        )
    return response


async def _application_response(app: Application) -> ApplicationResponse:
    skills = await SkillsTaxonomy.find_all().to_list()
    id_to_skill, _ = _skill_maps(skills)
    saved_ai_status = getattr(app, "ai_status", None)
    if saved_ai_status is None:
        saved_ai_status = "DONE" if app.ai_match_score is not None else "FAILED"
    response = _to_response(app, saved_ai_status, id_to_skill)
    job = await JobPosting.get(app.job_id)
    company = await Company.get(job.company_id) if job is not None else None
    return _attach_job_and_company(response, job, company)


async def list_candidate_applications(
    user: User,
    skip: int = 0,
    limit: int = 50,
) -> List[ApplicationResponse]:
    applications = (
        await Application.find(Application.candidate_id == user.id)
        .sort("-applied_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )
    if not applications:
        return []

    skills = await SkillsTaxonomy.find_all().to_list()
    id_to_skill, _ = _skill_maps(skills)

    job_ids = list({app.job_id for app in applications})
    jobs = await JobPosting.find({"_id": {"$in": job_ids}}).to_list() if job_ids else []
    jobs_by_id = {j.id: j for j in jobs}

    company_ids = list({j.company_id for j in jobs if getattr(j, "company_id", None) is not None})
    companies = await Company.find({"_id": {"$in": company_ids}}).to_list() if company_ids else []
    companies_by_id = {c.id: c for c in companies}

    results: List[ApplicationResponse] = []
    for app in applications:
        saved_ai_status = getattr(app, "ai_status", None)
        if saved_ai_status is None:
            saved_ai_status = "DONE" if app.ai_match_score is not None else "FAILED"
        resp = _to_response(app, saved_ai_status, id_to_skill)
        job = jobs_by_id.get(app.job_id)
        company = companies_by_id.get(job.company_id) if job is not None else None
        results.append(_attach_job_and_company(resp, job, company))
    return results


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
    """Chỉ ứng viên chủ đơn, hoặc nhà tuyển dụng sở hữu tin tuyển dụng (cùng công ty), được xem.

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
        if (
            job is None
            or job.recruiter_id != user.id
            or (user.company_id is not None and job.company_id != user.company_id)
        ):
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
    weights_snapshot = None
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
            weights_snapshot = _extract_weights_snapshot(job, ai)
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
        ai_match_score=score,
        matching_version=version,
        matching_weights_snapshot=weights_snapshot,
        ai_analysis=analysis,
        ai_status=ai_status,
        ai_analyzed_at=datetime.utcnow() if score is not None else None,
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


async def list_job_applications_ranked(
    user: User,
    job_id: str,
    pipeline_status: Optional[str] = None,
    min_ai_score: Optional[float] = None,
) -> List[RankedApplicationItem]:
    """Liệt kê và xếp hạng ứng viên của tin tuyển dụng thuộc recruiter hiện tại."""
    try:
        object_id = PydanticObjectId(job_id)
    except (InvalidId, TypeError):
        raise CVError(403, "Bạn không có quyền xem ứng viên của tin tuyển dụng này")

    job = await JobPosting.get(object_id)
    if job is None or job.deleted_at is not None or job.recruiter_id != user.id:
        raise CVError(403, "Bạn không có quyền xem ứng viên của tin tuyển dụng này")

    match_filter: Dict[str, Any] = {"job_id": object_id}
    if pipeline_status is not None:
        match_filter["pipeline_status"] = pipeline_status
    if min_ai_score is not None:
        match_filter["ai_match_score"] = {"$gte": min_ai_score}

    pipeline = [
        {"$match": match_filter},
        {"$sort": {"ai_match_score": -1, "applied_at": -1}},
        {
            "$lookup": {
                "from": "users",
                "localField": "candidate_id",
                "foreignField": "_id",
                "as": "candidate",
            }
        },
        {
            "$unwind": {
                "path": "$candidate",
                "preserveNullAndEmptyArrays": True,
            }
        },
        {
            "$lookup": {
                "from": "skills_taxonomy",
                "localField": "ai_analysis.matched",
                "foreignField": "_id",
                "as": "matched_skill_docs",
            }
        },
        {
            "$lookup": {
                "from": "skills_taxonomy",
                "localField": "ai_analysis.missing",
                "foreignField": "_id",
                "as": "missing_skill_docs",
            }
        },
        {
            "$project": {
                "_id": 1,
                "candidate_id": 1,
                "ai_match_score": 1,
                "ai_status": 1,
                "matching_version": 1,
                "matching_weights_snapshot": 1,
                "score_breakdown": "$ai_analysis.score_breakdown",
                "pipeline_status": 1,
                "applied_at": 1,
                "full_name": {"$ifNull": ["$candidate.full_name", ""]},
                "email": {"$ifNull": ["$candidate.email", ""]},
                "phone": {
                    "$ifNull": [
                        "$candidate.phone",
                        "$candidate.profile.phone",
                    ]
                },
                "matched_skills": {
                    "$map": {
                        "input": {"$ifNull": ["$matched_skill_docs", []]},
                        "as": "skill",
                        "in": {"id": "$$skill._id", "name": "$$skill.name"},
                    }
                },
                "missing_skills": {
                    "$map": {
                        "input": {"$ifNull": ["$missing_skill_docs", []]},
                        "as": "skill",
                        "in": {"id": "$$skill._id", "name": "$$skill.name"},
                    }
                },
            }
        },
    ]
    rows = await Application.get_motor_collection().aggregate(pipeline).to_list(
        length=None
    )

    return [
        RankedApplicationItem(
            id=row["_id"],
            candidate_id=row["candidate_id"],
            full_name=row.get("full_name") or "",
            email=row.get("email") or "",
            phone=row.get("phone"),
            ai_match_score=row.get("ai_match_score"),
            ai_status="DONE" if row.get("ai_status") == "COMPLETED" else (
                row.get("ai_status")
                or ("DONE" if row.get("ai_match_score") is not None else "FAILED")
            ),
            matching_version=row.get("matching_version"),
            score_breakdown=row.get("score_breakdown"),
            matching_weights_snapshot=_to_weights_schema(
                row.get("matching_weights_snapshot")
            ),
            pipeline_status=row["pipeline_status"],
            applied_at=row["applied_at"],
            matched_skills=[
                RankedSkillItem(id=skill["id"], name=skill["name"])
                for skill in row.get("matched_skills", [])
            ],
            missing_skills=[
                RankedSkillItem(id=skill["id"], name=skill["name"])
                for skill in row.get("missing_skills", [])
            ],
            cv_preview_url=f"/api/v1/applications/{row['_id']}/cv",
        )
        for row in rows
    ]


VIETNAM_TZ = timezone(timedelta(hours=7))


def _to_naive_local(value: datetime) -> datetime:
    """Lịch phỏng vấn lưu theo giờ Việt Nam (naive) để thông báo/email hiển thị đúng giờ HR nhập."""
    if value.tzinfo is not None:
        value = value.astimezone(VIETNAM_TZ).replace(tzinfo=None)
    return value.replace(microsecond=0)


def _build_interview_schedule(payload: ApplicationStatusUpdate) -> Optional[Dict[str, Any]]:
    schedule = payload.interview_schedule
    if schedule is None:
        return None
    if payload.pipeline_status != "INTERVIEW":
        raise CVError(422, "Chỉ được gửi lịch phỏng vấn khi chuyển sang trạng thái INTERVIEW")
    location = (schedule.location or "").strip()
    link = (schedule.link or "").strip()
    if not location and not link:
        raise CVError(422, "Lịch phỏng vấn cần có địa điểm hoặc link phỏng vấn online")
    return {"time": _to_naive_local(schedule.time), "location": location or None, "link": link or None}


async def update_application_status(
    user: User,
    application_id: PydanticObjectId,
    payload: ApplicationStatusUpdate,
    background_tasks: Optional[BackgroundTasks] = None,
) -> ApplicationStatusResponse:
    """PATCH /applications/{id}/status: chỉ RECRUITER sở hữu tin tuyển dụng của đơn này.

    - Đổi pipeline_status (APPLIED | SCREENING | INTERVIEW | HIRED | REJECTED).
    - Nhận recruiter_note (ghi chú nội bộ, ứng viên không thấy) và interview_schedule { time, location, link }.
    - Mỗi lần đổi trạng thái (hoặc gửi lịch mới) đẩy thêm 1 bản ghi { status, changed_by, time } vào status_history.
    - Gọi notification_service để báo cho ứng viên (thông báo trong hệ thống + email).
    """
    app = await Application.get(application_id)
    if app is None:
        raise CVError(404, "Không tìm thấy hồ sơ ứng tuyển")
    job = await JobPosting.get(app.job_id)
    if job is None or job.deleted_at is not None:
        raise CVError(404, "Không tìm thấy tin tuyển dụng của hồ sơ này")
    if (
        user.user_type != "RECRUITER"
        or job.recruiter_id != user.id
        or (user.company_id is not None and job.company_id != user.company_id)
    ):
        raise CVError(403, "Bạn không có quyền cập nhật hồ sơ ứng tuyển này")

    new_status = payload.pipeline_status
    status_changed = new_status != app.pipeline_status
    schedule = _build_interview_schedule(payload)
    schedule_changed = schedule is not None and schedule != app.interview_schedule
    if new_status == "INTERVIEW" and status_changed and schedule is None and not app.interview_schedule:
        raise CVError(422, "Cần nhập lịch phỏng vấn (thời gian và địa điểm hoặc link) khi chuyển sang INTERVIEW")

    now = datetime.utcnow()
    if "recruiter_note" in payload.model_fields_set:
        app.recruiter_note = (payload.recruiter_note or "").strip() or None
    if schedule is not None:
        app.interview_schedule = schedule
    if status_changed or schedule_changed:
        app.pipeline_status = new_status
        app.status_history.append(StatusHistory(status=new_status, changed_by=user.id, time=now))
    app.updated_at = now
    await app.save()

    # Hàm thông báo của Cường không bao giờ raise; đổi trạng thái đã kèm lịch nên chỉ gửi 1 thông báo,
    # và không gửi thông báo/email trùng lặp khi không có thay đổi thực tế.
    if status_changed:
        await notification_service.notify_application_status(app, background_tasks, new_status)
    elif schedule_changed:
        await notification_service.notify_interview_schedule(app, background_tasks)

    return ApplicationStatusResponse(
        id=app.id,
        pipeline_status=app.pipeline_status,
        recruiter_note=app.recruiter_note,
        interview_schedule=app.interview_schedule,
        status_history=[
            StatusHistoryItem(status=h.status, time=h.time, changed_by=h.changed_by)
            for h in app.status_history
        ],
        updated_at=app.updated_at,
    )

