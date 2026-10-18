from fastapi import APIRouter, UploadFile, File, HTTPException

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
    pdf_bytes = await file.read()
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
    "/embed",
    response_model=EmbeddingResponse,
    summary="Tạo vector nhúng phục vụ gợi ý việc làm (UC-Bổ sung 2)",
)
async def create_embedding_endpoint(payload: EmbeddingRequest):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Văn bản đầu vào không được để trống.")
    vector = SimilarityService.compute_embedding(payload.text)
    return EmbeddingResponse(embedding=vector, model_version=settings.MODEL_NAME)