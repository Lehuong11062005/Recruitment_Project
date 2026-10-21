import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.core.config import settings
from app.schemas.matching import (
    ParseCVResponse,
    MatchingRequest,
    MatchingResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)
from app.services.cv_parser import CVParserService
from app.services.similarity import SimilarityService

router = APIRouter()


@router.post(
    "/parse-cv",
    response_model=ParseCVResponse,
    summary="Bóc tách văn bản và kỹ năng từ file PDF CV (UC-AI1, UC-C3)",
)
async def parse_cv_endpoint(file: UploadFile = File(...)):
    pdf_bytes = await file.read(settings.MAX_PDF_SIZE_MB * 1024 * 1024 + 1)
    return CVParserService.parse_pdf_full(filename=file.filename or "cv.pdf", pdf_bytes=pdf_bytes)


@router.post(
    "/match",
    response_model=MatchingResponse,
    summary="Tính điểm % Matching và phân tích kỹ năng CV - JD (UC-AI2, UC-C5, UC-C6)",
)
async def match_cv_jd_endpoint(payload: MatchingRequest):
    if not payload.cv_text.strip() or not payload.jd_text.strip():
        raise HTTPException(status_code=400, detail="cv_text và jd_text không được để trống.")
    return SimilarityService.evaluate_cv_jd(payload)


@router.post(
    "/match-cv",
    response_model=MatchingResponse,
    summary="Phân tích CV PDF và so khớp với JD gửi qua multipart/form-data",
)
async def match_uploaded_cv_endpoint(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
    required_skills: str = Form(""),
    candidate_experience_years: float = Form(0.0, ge=0),
    job_experience_required: float = Form(0.0, ge=0),
):
    pdf_bytes = await file.read(settings.MAX_PDF_SIZE_MB * 1024 * 1024 + 1)
    parsed = CVParserService.parse_pdf_full(
        filename=file.filename or "cv.pdf",
        pdf_bytes=pdf_bytes,
    )
    if not parsed.parsed_text.strip() or not jd_text.strip():
        raise HTTPException(status_code=400, detail="CV và mô tả công việc không được để trống.")
    try:
        parsed_skills = json.loads(required_skills) if required_skills.strip().startswith("[") else required_skills.split(",")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="required_skills phải là JSON array hoặc danh sách phân tách bằng dấu phẩy") from exc
    if not isinstance(parsed_skills, list) or any(not isinstance(item, str) for item in parsed_skills):
        raise HTTPException(status_code=422, detail="required_skills phải là danh sách chuỗi")
    skills = [item.strip() for item in parsed_skills if item.strip()]
    return SimilarityService.evaluate_cv_jd(
        MatchingRequest(
            cv_text=parsed.parsed_text,
            jd_text=jd_text,
            candidate_skills=parsed.skills,
            required_skills=skills,
            candidate_experience_years=candidate_experience_years,
            job_experience_required=job_experience_required,
        )
    )


@router.post(
    "/embed",
    response_model=EmbeddingResponse,
    summary="Tạo vector nhúng phục vụ gợi ý việc làm (UC-Bổ sung 2)",
)
async def create_embedding_endpoint(payload: EmbeddingRequest):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Văn bản đầu vào không được để trống.")
    vector = SimilarityService.compute_embedding(payload.text)
    return EmbeddingResponse(embedding=vector, model_version=settings.MODEL_NAME)