import fitz
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.model_loader import ModelLoader
from app.main import app
from app.schemas.matching import MatchingRequest, MatchingWeights
from app.services.similarity import SimilarityService


class _DeterministicModel:
    """Deterministic embedding stub producing cosine similarity = 0.80 -> semantic_score = 80.0."""

    def __init__(self):
        self.calls = 0

    def encode(self, sentences, **kwargs):
        self.calls += 1
        if isinstance(sentences, str):
            return np.array([1.0, 0.0, 0.0])
        # dot([1, 0, 0], [0.8, 0.6, 0]) = 0.80 -> semantic_score = 80.0
        return np.array([[1.0, 0.0, 0.0], [0.8, 0.6, 0.0]])


def _sample_pdf(text: str = "Python FastAPI Docker developer") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 60), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_case_1_custom_weights_60_25_15():
    score, snap = SimilarityService.compute_weighted_score(
        skill_score=90,
        semantic_score=80,
        experience_score=80,
        weights={
            "skill_weight": 0.6,
            "semantic_weight": 0.25,
            "experience_weight": 0.15,
        },
    )
    assert score == 86.0
    assert snap.model_dump() == {
        "skill_weight": 0.6,
        "semantic_weight": 0.25,
        "experience_weight": 0.15,
    }


def test_case_2_default_weights_50_35_15():
    # (90, 80, 80) -> 90*0.50 + 80*0.35 + 80*0.15 = 45 + 28 + 12 = 85.0
    score_90, snap = SimilarityService.compute_weighted_score(
        skill_score=90,
        semantic_score=80,
        experience_score=80,
    )
    assert score_90 == 85.0
    assert snap.model_dump() == {
        "skill_weight": 0.5,
        "semantic_weight": 0.35,
        "experience_weight": 0.15,
    }

    # (89, 80, 80) -> 89*0.50 + 80*0.35 + 80*0.15 = 44.5 + 28 + 12 = 84.5
    score_89, _ = SimilarityService.compute_weighted_score(
        skill_score=89,
        semantic_score=80,
        experience_score=80,
    )
    assert score_89 == 84.5


def test_case_3_hundred_percent_skill_weight():
    score, snap = SimilarityService.compute_weighted_score(
        skill_score=90,
        semantic_score=80,
        experience_score=80,
        weights={
            "skill_weight": 1.0,
            "semantic_weight": 0.0,
            "experience_weight": 0.0,
        },
    )
    assert score == 90.0
    assert snap.skill_weight == 1.0
    assert snap.semantic_weight == 0.0
    assert snap.experience_weight == 0.0


@pytest.mark.parametrize(
    "invalid_weights",
    [
        {"skill_weight": 0.5, "semantic_weight": 0.2, "experience_weight": 0.1},     # sum < 1 (0.8)
        {"skill_weight": 0.6, "semantic_weight": 0.35, "experience_weight": 0.15},   # sum > 1 (1.1)
        {"skill_weight": 0.0, "semantic_weight": 0.0, "experience_weight": 0.0},     # sum == 0
        {"skill_weight": -0.1, "semantic_weight": 0.6, "experience_weight": 0.5},    # negative
        {"skill_weight": 1.2, "semantic_weight": 0.0, "experience_weight": 0.0},     # > 1
        {"skill_weight": 0.6, "semantic_weight": 0.4},                               # missing field
        {"skill_weight": True, "semantic_weight": 0.0, "experience_weight": 0.0},    # boolean rejected
        {
            "skill_weight": 0.5,
            "semantic_weight": 0.35,
            "experience_weight": 0.15,
            "extra": 0.1,
        },
    ],
)
def test_case_4_invalid_weights_rejected_before_scoring(monkeypatch, invalid_weights):
    stub_model = _DeterministicModel()
    monkeypatch.setattr(ModelLoader, "model", stub_model)

    with pytest.raises(ValidationError):
        MatchingWeights.model_validate(invalid_weights)

    client = TestClient(app)
    resp = client.post(
        "/api/v1/ai/match",
        json={
            "cv_text": "Python developer",
            "jd_text": "Python developer",
            "matching_weights": invalid_weights,
        },
    )
    assert resp.status_code == 422
    assert stub_model.calls == 0  # Rejected prior to Sentence-BERT inference


def test_match_endpoint_edge_cases_and_snapshot(monkeypatch):
    stub_model = _DeterministicModel()
    monkeypatch.setattr(ModelLoader, "model", stub_model)
    client = TestClient(app)

    # Edge case A: JD with no required skills, CV missing experience (0 vs 4 years), IEEE-754 0.1+0.2+0.7
    resp_a = client.post(
        "/api/v1/ai/match",
        json={
            "cv_text": "Nhân viên hành chính văn phòng",
            "jd_text": "Tuyển nhân viên hành chính văn phòng tổng hợp",
            "candidate_skills": [],
            "required_skills": [],
            "candidate_experience_years": 0,
            "job_experience_required": 4,
            "matching_weights": {
                "skill_weight": 0.1,
                "semantic_weight": 0.2,
                "experience_weight": 0.7,
            },
        },
    )
    assert resp_a.status_code == 200, resp_a.text
    body_a = resp_a.json()
    # skill_score=100.0 (no required skills), semantic_score=80.0, experience_score=0.0
    # 100*0.1 + 80*0.2 + 0*0.7 = 10 + 16 + 0 = 26.0
    assert body_a["ai_match_score"] == 26.0
    assert body_a["matching_version"] == "v2.0-configurable"
    assert body_a["matching_weights_snapshot"] == {
        "skill_weight": 0.1,
        "semantic_weight": 0.2,
        "experience_weight": 0.7,
    }
    assert body_a["score_breakdown"]["skill_score"] == 100.0
    assert body_a["score_breakdown"]["semantic_score"] == 80.0
    assert body_a["score_breakdown"]["experience_score"] == 0.0

    # Edge case B: CV missing all required skills (skill_score = 0.0), custom weights 60/25/15
    resp_b = client.post(
        "/api/v1/ai/match",
        json={
            "cv_text": "Kinh nghiệm kế toán doanh nghiệp",
            "jd_text": "Tuyển Python FastAPI Developer",
            "candidate_skills": [],
            "required_skills": ["Python", "FastAPI"],
            "candidate_experience_years": 4,
            "job_experience_required": 5,  # experience_score = 80.0
            "weights": {
                "skill_weight": 0.6,
                "semantic_weight": 0.25,
                "experience_weight": 0.15,
            },
        },
    )
    assert resp_b.status_code == 200, resp_b.text
    body_b = resp_b.json()
    # skill=0, semantic=80, exp=80 -> 0*0.6 + 80*0.25 + 80*0.15 = 32.0
    assert body_b["ai_match_score"] == 32.0

    # Multipart /match-cv endpoint with custom weights and invalid weights
    pdf_bytes = _sample_pdf("Python FastAPI developer")
    resp_cv_ok = client.post(
        "/api/v1/ai/match-cv",
        data={
            "jd_text": "Cần tuyển Python FastAPI",
            "required_skills": '["Python", "FastAPI"]',
            "candidate_experience_years": "4",
            "job_experience_required": "5",
            "matching_weights": '{"skill_weight": 0.6, "semantic_weight": 0.25, "experience_weight": 0.15}',
        },
        files={"file": ("cv.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp_cv_ok.status_code == 200, resp_cv_ok.text
    # skill=100, semantic=80, exp=80 -> 100*0.6 + 80*0.25 + 80*0.15 = 60 + 20 + 12 = 92.0
    assert resp_cv_ok.json()["ai_match_score"] == 92.0

    resp_cv_bad = client.post(
        "/api/v1/ai/match-cv",
        data={
            "jd_text": "Cần tuyển Python FastAPI",
            "matching_weights": '{"skill_weight": 0.8, "semantic_weight": 0.5, "experience_weight": 0.1}',
        },
        files={"file": ("cv.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp_cv_bad.status_code == 422
