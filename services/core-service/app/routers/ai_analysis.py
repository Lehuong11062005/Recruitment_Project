import asyncio
import math
from datetime import datetime
from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.deps import get_current_candidate, get_current_user
from app.core.config import settings
from app.core.storage import CV_DIR
from app.models.application import AIAnalysis, Application
from app.models.job import JobPosting
from app.models.skill import SkillsTaxonomy
from app.models.user import User
from app.schemas.application import AIAnalysisResponse, ApplicationResponse, SkillRef
from app.services import application_service
from app.services.cv_service import read_limited
from app.services.cv_utils import CVError, match_skill_names, validate_pdf

router = APIRouter()


class AIPreviewResponse(BaseModel):
    parsed_text: str
    skills: List[SkillRef] = Field(default_factory=list)
    ai_match_score: float
    matching_version: str
    embedding_vector: List[float] = Field(default_factory=list)
    ai_analysis: AIAnalysisResponse


def _taxonomy_data(skills: list[SkillsTaxonomy]) -> tuple[list[dict], dict]:
    taxonomy = [
        {"id": skill.id, "name": skill.name, "aliases": skill.aliases, "category": skill.category}
        for skill in skills
    ]
    id_to_name = {skill.id: skill.name for skill in skills}
    return taxonomy, id_to_name


def _map_analysis(payload: dict, taxonomy: list[dict]) -> AIAnalysis:
    raw = payload["ai_analysis"]
    matched = match_skill_names(raw["matched"], taxonomy)
    missing = match_skill_names(raw["missing"], taxonomy)
    return AIAnalysis(
        matched=[item["id"] for item in matched],
        missing=[item["id"] for item in missing],
        score_breakdown={
            key: float(value) for key, value in raw["score_breakdown"].items()
        },
        recommendation=raw["recommendation"],
    )


async def _get_job(job_id: str, require_open: bool = False) -> JobPosting:
    try:
        oid = PydanticObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=422, detail="job_id không hợp lệ")
    job = await JobPosting.get(oid)
    if job is None or job.deleted_at is not None or (require_open and job.status != "OPEN"):
        raise HTTPException(status_code=404, detail="Không tìm thấy tin tuyển dụng đang mở")
    return job


async def _analyze_file(
    job: JobPosting,
    filename: str,
    data: bytes,
    candidate_experience_years: float = 0.0,
) -> tuple[dict, dict, list[SkillsTaxonomy]]:
    parsed = await application_service._call_ai_parse(filename, data)
    if parsed is None:
        raise HTTPException(status_code=503, detail="AI Service hiện chưa thể phân tích CV")
    skills = await SkillsTaxonomy.find_all().to_list()
    _, id_to_name = _taxonomy_data(skills)
    required_names = [id_to_name[item] for item in job.required_skills if item in id_to_name]
    result = await application_service._call_ai_match(
        parsed["parsed_text"],
        parsed["skills"],
        job,
        required_names,
        candidate_experience_years,
    )
    if result is None:
        raise HTTPException(status_code=503, detail="AI Service hiện chưa thể so khớp CV với JD")
    return parsed, result, skills


@router.post("/preview", response_model=AIPreviewResponse, summary="Xem trước điểm AI Matching cho CV và JD")
async def preview_ai_matching(
    job_id: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_candidate),
):
    job = await _get_job(job_id, require_open=True)
    max_bytes = settings.CV_MAX_SIZE_MB * 1024 * 1024
    try:
        data = await read_limited(file, max_bytes)
        validate_pdf(file.filename or "", data, max_bytes)
    except CVError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    parsed, result, skills = await _analyze_file(
        job,
        file.filename or "cv.pdf",
        data,
        application_service._candidate_experience_years(user),
    )
    taxonomy, _ = _taxonomy_data(skills)
    candidate_skills = match_skill_names(parsed["skills"], taxonomy)
    analysis = _map_analysis(result, taxonomy)
    return AIPreviewResponse(
        parsed_text=parsed["parsed_text"],
        skills=[SkillRef(id=item["id"], name=item["name"], category=item.get("category")) for item in candidate_skills],
        ai_match_score=float(result["ai_match_score"]),
        matching_version=result["matching_version"],
        embedding_vector=[
            float(value)
            for value in result.get("embedding_vector", parsed["embedding_vector"])
        ],
        ai_analysis=AIAnalysisResponse(
            matched=[SkillRef(id=item, category=next((s.get("category") for s in taxonomy if s["id"] == item), None), name=next((s["name"] for s in taxonomy if s["id"] == item), "")) for item in analysis.matched],
            missing=[SkillRef(id=item, category=next((s.get("category") for s in taxonomy if s["id"] == item), None), name=next((s["name"] for s in taxonomy if s["id"] == item), "")) for item in analysis.missing],
            score_breakdown=analysis.score_breakdown,
            recommendation=analysis.recommendation,
        ),
    )


async def _owned_application(application_id: str, user: User) -> Application:
    try:
        oid = PydanticObjectId(application_id)
    except Exception:
        raise HTTPException(status_code=422, detail="application_id không hợp lệ")
    app = await Application.get(oid)
    if app is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ ứng tuyển")
    job = await JobPosting.get(app.job_id)
    is_candidate_owner = user.user_type == "CANDIDATE" and app.candidate_id == user.id
    is_recruiter_owner = (
        user.user_type == "RECRUITER" and job is not None and job.recruiter_id == user.id
    )
    if not is_candidate_owner and not is_recruiter_owner:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem hồ sơ ứng tuyển này")
    return app


@router.get(
    "/applications/{application_id}",
    response_model=ApplicationResponse,
    summary="Xem chi tiết kết quả AI của hồ sơ ứng tuyển",
)
async def get_ai_analysis(
    application_id: str,
    user: User = Depends(get_current_user),
):
    app = await _owned_application(application_id, user)
    return await application_service._application_response(app)


@router.post(
    "/applications/{application_id}/retry",
    response_model=ApplicationResponse,
    summary="Phân tích lại CV ứng tuyển bằng AI",
)
async def retry_ai_analysis(
    application_id: str,
    user: User = Depends(get_current_user),
):
    app = await _owned_application(application_id, user)
    cv_path = CV_DIR / str(app.candidate_id) / app.cv_url.rsplit("/", 1)[-1]
    if not cv_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy file CV đã lưu")

    data = await asyncio.to_thread(cv_path.read_bytes)
    max_bytes = settings.CV_MAX_SIZE_MB * 1024 * 1024
    try:
        validate_pdf(cv_path.name, data, max_bytes)
    except CVError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    job = await JobPosting.get(app.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tin tuyển dụng")
    candidate = await User.get(app.candidate_id)
    experience_years = (
        application_service._candidate_experience_years(candidate)
        if candidate is not None
        else 0.0
    )
    parsed, result, skills = await _analyze_file(
        job,
        cv_path.name,
        data,
        experience_years,
    )
    taxonomy, id_to_name = _taxonomy_data(skills)
    app.parsed_text = parsed["parsed_text"]
    app.embedding_vector = [
        float(value)
        for value in result.get("embedding_vector", parsed["embedding_vector"])
        if isinstance(value, (int, float)) and math.isfinite(value)
    ]
    app.ai_match_score = float(result["ai_match_score"])
    app.matching_version = result["matching_version"]
    app.ai_analysis = _map_analysis(result, taxonomy)
    app.updated_at = datetime.utcnow()
    await app.save()
    return await application_service._application_response(app)
