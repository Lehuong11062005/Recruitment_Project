import re
import unicodedata
from typing import Dict, List

import numpy as np
import torch

from app.core.config import settings
from app.core.model_loader import ModelLoader
from app.schemas.matching import (
    AIAnalysisBreakdown,
    MatchingRequest,
    MatchingResponse,
)
from app.services.cv_parser import CVParserService


class SimilarityService:
    @classmethod
    def compute_embedding(cls, text: str) -> List[float]:
        model = ModelLoader.get_model()
        with torch.inference_mode():
            embedding = model.encode(
                CVParserService.clean_text(text),
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        return np.asarray(embedding).reshape(-1).tolist()

    @staticmethod
    def _normalize_skill(skill: str) -> str:
        return unicodedata.normalize("NFKC", skill).casefold().strip()

    @classmethod
    def _skill_aliases(cls) -> Dict[str, str]:
        aliases: Dict[str, str] = {}
        for item in CVParserService.get_taxonomy():
            canonical = item.get("skill", "").strip()
            if not canonical:
                continue
            for name in [canonical, *item.get("aliases", [])]:
                if isinstance(name, str) and name.strip():
                    aliases[cls._normalize_skill(name)] = canonical
        return aliases

    @classmethod
    def evaluate_cv_jd(cls, payload: MatchingRequest) -> MatchingResponse:
        model = ModelLoader.get_model()
        cv_text = CVParserService.clean_text(payload.cv_text)
        jd_text = CVParserService.clean_text(payload.jd_text)

        with torch.inference_mode():
            embeddings = model.encode(
                [cv_text, jd_text],
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        cv_embedding, jd_embedding = np.asarray(embeddings, dtype=float)
        cosine_similarity = float(np.dot(cv_embedding, jd_embedding))
        semantic_score = round(max(0.0, min(100.0, cosine_similarity * 100.0)), 1)

        aliases = cls._skill_aliases()
        requested = payload.required_skills or CVParserService.extract_skills(jd_text)
        required_skills = list(dict.fromkeys(
            aliases.get(cls._normalize_skill(skill), skill.strip())
            for skill in requested if skill.strip()
        ))
        candidate_skills = [
            *payload.candidate_skills,
            *CVParserService.extract_skills(cv_text),
        ]
        candidate_canonical = {
            aliases.get(cls._normalize_skill(skill), skill.strip())
            for skill in candidate_skills if skill.strip()
        }

        matched: List[str] = []
        missing: List[str] = []
        for required in required_skills:
            if required in candidate_canonical:
                matched.append(required)
                continue
            terms = [
                alias for alias, canonical in aliases.items()
                if canonical.casefold() == required.casefold()
            ]
            if any(
                re.search(r"(?<![\w#+])" + re.escape(term) + r"(?![\w#+])", cv_text, re.IGNORECASE)
                for term in terms
            ):
                matched.append(required)
            else:
                missing.append(required)

        skill_score = (
            round(len(matched) / len(required_skills) * 100.0, 1)
            if required_skills else 100.0
        )
        if payload.job_experience_required <= 0 or (
            payload.candidate_experience_years >= payload.job_experience_required
        ):
            experience_score = 100.0
        else:
            experience_score = round(
                max(0.0, payload.candidate_experience_years)
                / payload.job_experience_required * 100.0,
                1,
            )

        final_score = round(
            settings.SKILL_WEIGHT * skill_score
            + settings.SEMANTIC_WEIGHT * semantic_score
            + settings.EXPERIENCE_WEIGHT * experience_score,
            1,
        )
        level = (
            "rất phù hợp" if final_score >= 80
            else "khá phù hợp" if final_score >= 60
            else "chưa phù hợp cao"
        )
        matched_text = ", ".join(matched[:5]) if matched else "chưa có kỹ năng yêu cầu nào được khớp"
        missing_text = ", ".join(missing[:5]) if missing else "không có kỹ năng bắt buộc nào còn thiếu"
        recommendation = (
            f"Hồ sơ {level} với vị trí (điểm {final_score:.1f}/100). "
            f"Kỹ năng khớp: {matched_text}. Cần lưu ý khi phỏng vấn: {missing_text}."
        )

        return MatchingResponse(
            ai_match_score=final_score,
            matching_version=settings.MATCHING_VERSION,
            embedding_vector=cv_embedding.tolist(),
            ai_analysis=AIAnalysisBreakdown(
                matched=matched,
                missing=missing,
                matched_skills=matched,
                missing_skills=missing,
                score_breakdown={
                    "skill_score": skill_score,
                    "experience_score": experience_score,
                    "semantic_score": semantic_score,
                    "skill_match": skill_score,
                    "semantic_match": semantic_score,
                    "experience_match": experience_score,
                },
                recommendation=recommendation,
            ),
        )
