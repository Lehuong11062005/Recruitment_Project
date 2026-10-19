import re
from typing import List
from sentence_transformers import util

from app.core.config import settings
from app.core.model_loader import ModelLoader
from app.schemas.matching import (
    MatchingRequest,
    MatchingResponse,
    AIAnalysisBreakdown,
)
from app.services.cv_parser import CVParserService


class SimilarityService:
    @classmethod
    def compute_embedding(cls, text: str) -> List[float]:
        model = ModelLoader.get_model()
        return model.encode(text).tolist()

    @classmethod
    def evaluate_cv_jd(cls, payload: MatchingRequest) -> MatchingResponse:
        model = ModelLoader.get_model()

        # 1. Tính Cosine Similarity bằng Sentence-BERT
        cv_tensor = model.encode(payload.cv_text, convert_to_tensor=True)
        jd_tensor = model.encode(payload.jd_text, convert_to_tensor=True)
        cos_sim = float(util.cos_sim(cv_tensor, jd_tensor).item())
        semantic_score = round(max(0.0, min(100.0, cos_sim * 100.0)), 1)

        # 2. Lấy danh sách kỹ năng yêu cầu của JD
        required_skills = payload.required_skills or CVParserService.extract_skills(payload.jd_text)

        # 3. Đối chiếu kỹ năng khớp (matched) và thiếu (missing)
        cand_lower = {s.lower().strip() for s in payload.candidate_skills}
        extracted_cv_lower = {s.lower().strip() for s in CVParserService.extract_skills(payload.cv_text)}
        all_cand_skills = cand_lower | extracted_cv_lower

        matched: List[str] = []
        missing: List[str] = []

        for req in required_skills:
            req_clean = req.strip()
            pattern = r"(?<![\w#+])" + re.escape(req_clean) + r"(?![\w#+])"
            if req_clean.lower() in all_cand_skills or re.search(pattern, payload.cv_text, re.IGNORECASE):
                matched.append(req_clean)
            else:
                missing.append(req_clean)

        if required_skills:
            skill_score = round((len(matched) / len(required_skills)) * 100.0, 1)
        else:
            skill_score = semantic_score

        # 4. Điểm kinh nghiệm
        if payload.job_experience_required <= 0:
            exp_score = 100.0
        else:
            exp_score = round(
                min(100.0, (payload.candidate_experience_years / payload.job_experience_required) * 100.0), 1
            )

        # 5. Điểm tổng hợp theo trọng số trong app/core/config.py
        final_score = round(
            settings.SKILL_WEIGHT * skill_score
            + settings.SEMANTIC_WEIGHT * semantic_score
            + settings.EXPERIENCE_WEIGHT * exp_score,
            1,
        )

        if final_score >= 80:
            recommendation = "Hồ sơ rất phù hợp với vị trí tuyển dụng. Khuyến nghị ưu tiên phỏng vấn."
        elif final_score >= 60:
            recommendation = "Hồ sơ khá phù hợp, tuy nhiên ứng viên cần bổ sung một số kỹ năng còn thiếu."
        else:
            recommendation = "Độ tương thích hiện tại còn thấp so với yêu cầu chuyên môn của công việc."

        return MatchingResponse(
            ai_match_score=final_score,
            matching_version=settings.MATCHING_VERSION,
            embedding_vector=cv_tensor.cpu().tolist(),
            ai_analysis=AIAnalysisBreakdown(
                matched=matched,
                missing=missing,
                score_breakdown={
                    "skill_match": skill_score,
                    "semantic_match": semantic_score,
                    "experience_match": exp_score,
                },
                recommendation=recommendation,
            ),
        )