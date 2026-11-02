import time
import unicodedata

import fitz
import numpy as np
import pytest
from fastapi import HTTPException

from app.core.model_loader import ModelLoader
from app.schemas.matching import MatchingRequest
from app.services.cv_parser import CVParserService, clean_text
from app.services.similarity import SimilarityService


class _FastModel:
    def encode(self, sentences, **kwargs):
        if isinstance(sentences, str):
            return np.array([1.0, 0.0, 0.0])
        return np.array([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])


def _pdf_with_columns_and_table() -> bytes:
    document = fitz.open()
    page = document.new_page(width=600, height=800)
    page.insert_text((40, 50), "LEFT COLUMN TOP")
    page.insert_text((40, 80), "LEFT COLUMN BOTTOM")
    page.insert_text((340, 50), "RIGHT COLUMN TOP")
    page.insert_text((340, 80), "RIGHT COLUMN BOTTOM")
    page.insert_text((40, 140), "SKILL | YEARS")
    page.insert_text((40, 165), "Python | 5")
    result = document.tobytes()
    document.close()
    return result


def test_clean_text_normalizes_vietnamese_and_keeps_technical_names():
    decomposed = unicodedata.normalize("NFD", "Kỹ năng")
    cleaned = clean_text(f"{decomposed} • ★ \ufffd \ue000 C++ C# .NET Node.js")

    assert unicodedata.is_normalized("NFC", cleaned)
    assert "Kỹ năng" in cleaned
    assert all(value in cleaned for value in ("C++", "C#", ".NET", "Node.js"))
    assert all(value not in cleaned for value in ("•", "★", "\ufffd", "\ue000"))


def test_extract_pdf_preserves_column_order_and_table_text():
    extracted = CVParserService.extract_text_from_pdf(_pdf_with_columns_and_table())

    assert extracted.index("LEFT COLUMN TOP") < extracted.index("LEFT COLUMN BOTTOM")
    assert extracted.index("LEFT COLUMN BOTTOM") < extracted.index("RIGHT COLUMN TOP")
    assert extracted.index("RIGHT COLUMN TOP") < extracted.index("RIGHT COLUMN BOTTOM")
    assert "SKILL" in extracted
    assert "Python" in extracted


def test_extract_pdf_rejects_large_files_and_invalid_header(monkeypatch):
    monkeypatch.setattr("app.services.cv_parser.settings.MAX_PDF_SIZE_MB", 1)

    with pytest.raises(HTTPException) as too_large:
        CVParserService.extract_text_from_pdf(b"%PDF-" + b"x" * (1024 * 1024))
    assert too_large.value.status_code == 413

    with pytest.raises(HTTPException) as invalid:
        CVParserService.extract_text_from_pdf(b"not-a-pdf")
    assert invalid.value.status_code == 400


def test_similarity_resolves_skill_aliases_and_returns_breakdown(monkeypatch):
    monkeypatch.setattr(ModelLoader, "model", _FastModel())
    response = SimilarityService.evaluate_cv_jd(
        MatchingRequest(
            cv_text="Đã phát triển ứng dụng bằng React.js",
            jd_text="Cần kinh nghiệm ReactJS",
            candidate_skills=["React.js"],
            required_skills=["ReactJS"],
            candidate_experience_years=4,
            job_experience_required=3,
        )
    )

    analysis = response.ai_analysis
    assert analysis.matched == ["React"]
    assert analysis.matched_skills == ["React"]
    assert analysis.missing == []
    assert {"skill_score", "experience_score", "semantic_score"} <= set(analysis.score_breakdown)
    assert "React" in analysis.recommendation
    assert isinstance(response.ai_match_score, float)


def test_matching_pipeline_is_fast_after_warmup():
    if ModelLoader.model is None:
        from huggingface_hub import snapshot_download
        from huggingface_hub.errors import LocalEntryNotFoundError

        try:
            snapshot_download(
                repo_id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                local_files_only=True,
            )
        except LocalEntryNotFoundError:
            pytest.skip("The Sentence-BERT model is not present in the local Hugging Face cache")

    ModelLoader.load_model()
    request = MatchingRequest(
        cv_text="Python developer with five years of experience",
        jd_text="Python developer",
        candidate_skills=["Python"],
        required_skills=["Python"],
        candidate_experience_years=5,
        job_experience_required=3,
    )
    ModelLoader.warm_up()

    started = time.perf_counter()
    SimilarityService.evaluate_cv_jd(request)
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0
