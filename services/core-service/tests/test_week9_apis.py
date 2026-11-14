from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_candidate, get_current_user
from app.core.deps import get_current_recruiter
from app.main import app
from app.models.application import Application
from app.models.company import Company
from app.models.job import JobPosting
from app.models.skill import SkillsTaxonomy
from app.models.user import User
from app.routers import ai_analysis
from app.schemas.application import ApplicationResponse
from app.services import application_service
from app.services.job_service import JobService

APPLICATION_ID = "64b000000000000000000001"
JOB_ID = "64b000000000000000000002"
CANDIDATE_ID = "64b000000000000000000003"


class _Query:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self):
        return self.rows


@pytest.fixture
def client():
    return TestClient(app)


def _application_response(app_record):
    return ApplicationResponse(
        id=app_record.id,
        job_id=app_record.job_id,
        candidate_id=app_record.candidate_id,
        cv_url=app_record.cv_url,
        pipeline_status="APPLIED",
        ai_status=app_record.ai_status,
        ai_match_score=app_record.ai_match_score,
        matching_version=app_record.matching_version,
        ai_analyzed_at=app_record.ai_analyzed_at,
        applied_at=app_record.applied_at,
    )


def test_get_application_ai_analysis_returns_result_and_404_403(client, monkeypatch):
    record = SimpleNamespace(
        id=APPLICATION_ID, job_id=JOB_ID, candidate_id=CANDIDATE_ID,
        cv_url="cv.pdf", ai_status="DONE", ai_match_score=91.0,
        matching_version="v1", ai_analyzed_at=None,
        applied_at="2026-01-01T00:00:00",
    )
    owner = SimpleNamespace(id="hr-1", role="USER", user_type="RECRUITER")
    monkeypatch.setattr(Application, "get", staticmethod(lambda _id: _async_value(record)))
    monkeypatch.setattr(JobPosting, "get", staticmethod(lambda _id: _async_value(
        SimpleNamespace(recruiter_id="hr-1")
    )))
    monkeypatch.setattr(
        application_service, "_application_response",
        lambda value: _async_value(_application_response(value)),
    )
    app.dependency_overrides[get_current_user] = lambda: owner
    try:
        response = client.get(f"/api/v1/applications/{APPLICATION_ID}/ai-analysis")
        assert response.status_code == 200
        assert response.json()["ai_match_score"] == 91.0
    finally:
        app.dependency_overrides.clear()

    async def missing(_id):
        return None

    monkeypatch.setattr(Application, "get", staticmethod(missing))
    app.dependency_overrides[get_current_user] = lambda: owner
    try:
        assert client.get("/api/v1/applications/{}/ai-analysis".format("64b000000000000000000004")).status_code == 404
    finally:
        app.dependency_overrides.clear()

    async def unauthorized_job(_id):
        return SimpleNamespace(recruiter_id="someone-else")

    monkeypatch.setattr(Application, "get", staticmethod(lambda _id: _async_value(record)))
    monkeypatch.setattr(JobPosting, "get", staticmethod(unauthorized_job))
    app.dependency_overrides[get_current_user] = lambda: owner
    try:
        assert client.get(f"/api/v1/applications/{APPLICATION_ID}/ai-analysis").status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_retry_rejects_non_failed_application(client, monkeypatch):
    record = SimpleNamespace(id=APPLICATION_ID, ai_status="DONE")
    monkeypatch.setattr(
        ai_analysis, "_owned_application",
        lambda _id, _user: _async_value(record),
    )
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="hr-1", role="USER", user_type="RECRUITER"
    )
    try:
        response = client.post(f"/api/v1/ai-analysis/{APPLICATION_ID}/retry")
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_retry_reprocesses_failed_application(client, monkeypatch, tmp_path):
    record = SimpleNamespace(
        id=APPLICATION_ID, ai_status="FAILED", ai_error="old error",
        candidate_id=CANDIDATE_ID, job_id=JOB_ID, cv_url=f"/cvs/{CANDIDATE_ID}/cv.pdf",
        ai_match_score=None, matching_version="v1", ai_analyzed_at=None,
        applied_at="2026-01-01T00:00:00", parsed_text=None,
        embedding_vector=None, ai_analysis=None, updated_at=None,
        save=lambda: _async_value(None),
    )
    # Bound document methods are normally async; use an explicit async mock.
    async def save_record():
        return None
    record.save = save_record
    monkeypatch.setattr(ai_analysis, "_owned_application", lambda _id, _user: _async_value(record))
    monkeypatch.setattr(ai_analysis, "CV_DIR", tmp_path)
    cv_path = tmp_path / CANDIDATE_ID / "cv.pdf"
    cv_path.parent.mkdir()
    cv_path.write_bytes(b"%PDF-1.4 test")
    monkeypatch.setattr(JobPosting, "get", staticmethod(lambda _id: _async_value(
        SimpleNamespace(id=JOB_ID, title="Python", description="", required_skills=[], experience_required=0)
    )))
    monkeypatch.setattr(User, "get", staticmethod(lambda _id: _async_value(None)))
    monkeypatch.setattr(SkillsTaxonomy, "find_all", staticmethod(lambda: _Query([])))
    monkeypatch.setattr(
        application_service, "_call_ai_parse",
        lambda *_args: _async_value({
            "parsed_text": "python", "skills": ["Python"], "embedding_vector": [1.0],
        }),
    )
    monkeypatch.setattr(
        application_service, "_call_ai_match",
        lambda *_args: _async_value({
            "ai_match_score": 88.0, "matching_version": "v2",
            "embedding_vector": [1.0],
            "ai_analysis": {
                "matched": [], "missing": [], "score_breakdown": {"skill_score": 100.0},
                "recommendation": "Phù hợp",
            },
        }),
    )
    monkeypatch.setattr(
        application_service, "_application_response",
        lambda value: _async_value(_application_response(value)),
    )
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="hr-1", role="USER", user_type="RECRUITER"
    )
    try:
        response = client.post(f"/api/v1/ai-analysis/{APPLICATION_ID}/retry")
        assert response.status_code == 200, response.text
        assert response.json()["ai_status"] == "DONE"
        assert response.json()["ai_match_score"] == 88.0
    finally:
        app.dependency_overrides.clear()


def test_recommendations_returns_top_five_open_jobs_in_similarity_order(client, monkeypatch):
    candidate = SimpleNamespace(
        user_type="CANDIDATE",
        profile=SimpleNamespace(candidate_embedding=[1.0, 0.0], skills=[]),
    )
    jobs = [
        SimpleNamespace(
            id=f"64b0000000000000000000{index:02d}", title=f"Job {index}", description="",
            company_id="company-pending" if index == 7 else "company-1",
            required_skills=[], level="MID",
            experience_required=0, salary=None, location="Remote",
            job_embedding_vector=vector,
            status="CLOSED" if index == 6 else "OPEN",
        )
        for index, vector in enumerate([
            [0.1, 0.9], [0.9, 0.1], [1.0, 0.0], [0.8, 0.2],
            [0.7, 0.3], [0.6, 0.4], [1.0, 0.0], [1.0, 0.0],
        ])
    ]

    monkeypatch.setattr(
        JobPosting,
        "find",
        staticmethod(lambda query: _Query(
            [job for job in jobs if query.get("status") == job.status]
        )),
    )
    monkeypatch.setattr(
        Company,
        "find",
        staticmethod(lambda _query: _Query([
            SimpleNamespace(id="company-1", name="NovaTech Verified", verification_status="VERIFIED"),
        ])),
    )
    monkeypatch.setattr(SkillsTaxonomy, "find_all", staticmethod(lambda: _Query([])))
    app.dependency_overrides[get_current_candidate] = lambda: candidate
    try:
        response = client.get("/api/v1/jobs/recommendations")
        assert response.status_code == 200, response.text
        items = response.json()["items"]
        assert len(items) == 5
        assert [item["id"] for item in items] == [
            "64b000000000000000000002",
            "64b000000000000000000001",
            "64b000000000000000000003",
            "64b000000000000000000004",
            "64b000000000000000000005",
        ]
        assert all(item["company_name"] == "NovaTech Verified" for item in items)
        assert all(items[index]["match_score"] >= items[index + 1]["match_score"] for index in range(4))
    finally:
        app.dependency_overrides.clear()


async def _async_value(value):
    return value


def test_list_ranked_job_applications_returns_score_order(client, monkeypatch):
    recruiter = SimpleNamespace(id="64b000000000000000000020", user_type="RECRUITER")
    job = SimpleNamespace(recruiter_id=recruiter.id, deleted_at=None)
    rows = [
        {
            "_id": "64b000000000000000000031",
            "candidate_id": "64b000000000000000000041",
            "full_name": "Candidate Low",
            "email": "low@example.com",
            "phone": None,
            "ai_match_score": 64.0,
            "ai_status": "DONE",
            "pipeline_status": "APPLIED",
            "applied_at": "2026-10-02T10:00:00",
            "matched_skills": [],
            "missing_skills": [],
        },
        {
            "_id": "64b000000000000000000032",
            "candidate_id": "64b000000000000000000042",
            "full_name": "Candidate High",
            "email": "high@example.com",
            "phone": "0123456789",
            "ai_match_score": 96.0,
            "ai_status": "DONE",
            "pipeline_status": "SCREENING",
            "applied_at": "2026-10-03T10:00:00",
            "matched_skills": [
                {"id": "64b000000000000000000051", "name": "Python"}
            ],
            "missing_skills": [
                {"id": "64b000000000000000000052", "name": "MongoDB"}
            ],
        },
    ]
    captured = {}

    async def get_job(_job_id):
        return job

    class _Aggregate:
        async def to_list(self, length=None):
            return sorted(
                rows,
                key=lambda row: (
                    row["ai_match_score"],
                    row["applied_at"],
                ),
                reverse=True,
            )

    class _Collection:
        def aggregate(self, pipeline):
            captured["pipeline"] = pipeline
            return _Aggregate()

    monkeypatch.setattr(JobPosting, "get", staticmethod(get_job))
    monkeypatch.setattr(
        Application,
        "get_motor_collection",
        staticmethod(lambda: _Collection()),
    )
    app.dependency_overrides[get_current_recruiter] = lambda: recruiter
    try:
        response = client.get(f"/api/v1/jobs/{JOB_ID}/applications")
        assert response.status_code == 200, response.text
        items = response.json()
        assert [item["ai_match_score"] for item in items] == [96.0, 64.0]
        assert items[0]["full_name"] == "Candidate High"
        assert items[0]["matched_skills"] == [
            {"id": "64b000000000000000000051", "name": "Python"}
        ]
        assert items[0]["missing_skills"] == [
            {"id": "64b000000000000000000052", "name": "MongoDB"}
        ]
        assert items[0]["cv_preview_url"] == (
            f"/api/v1/applications/{items[0]['id']}/cv"
        )
        assert captured["pipeline"][1]["$sort"] == {
            "ai_match_score": -1,
            "applied_at": -1,
        }
    finally:
        app.dependency_overrides.clear()


def test_list_ranked_job_applications_forbidden_for_missing_or_unowned_job(
    client, monkeypatch
):
    recruiter = SimpleNamespace(id="64b000000000000000000020", user_type="RECRUITER")

    async def get_missing_job(_job_id):
        return None

    monkeypatch.setattr(JobPosting, "get", staticmethod(get_missing_job))
    app.dependency_overrides[get_current_recruiter] = lambda: recruiter
    try:
        assert client.get(
            f"/api/v1/jobs/{JOB_ID}/applications"
        ).status_code == 403

        async def get_unowned_job(_job_id):
            return SimpleNamespace(
                recruiter_id="64b000000000000000000099",
                deleted_at=None,
            )

        monkeypatch.setattr(JobPosting, "get", staticmethod(get_unowned_job))
        assert client.get(
            f"/api/v1/jobs/{JOB_ID}/applications"
        ).status_code == 403
        assert client.get(
            "/api/v1/jobs/not-an-object-id/applications"
        ).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_list_ranked_job_applications_returns_empty_array(client, monkeypatch):
    recruiter = SimpleNamespace(id="64b000000000000000000020", user_type="RECRUITER")

    async def get_job(_job_id):
        return SimpleNamespace(recruiter_id=recruiter.id, deleted_at=None)

    class _Aggregate:
        async def to_list(self, length=None):
            return []

    class _Collection:
        def aggregate(self, _pipeline):
            return _Aggregate()

    monkeypatch.setattr(JobPosting, "get", staticmethod(get_job))
    monkeypatch.setattr(
        Application,
        "get_motor_collection",
        staticmethod(lambda: _Collection()),
    )
    app.dependency_overrides[get_current_recruiter] = lambda: recruiter
    try:
        response = client.get(f"/api/v1/jobs/{JOB_ID}/applications")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_list_ranked_job_applications_passes_filters_to_match(client, monkeypatch):
    recruiter = SimpleNamespace(id="64b000000000000000000020", user_type="RECRUITER")
    captured = {}

    async def get_job(_job_id):
        return SimpleNamespace(recruiter_id=recruiter.id, deleted_at=None)

    class _Aggregate:
        async def to_list(self, length=None):
            return []

    class _Collection:
        def aggregate(self, pipeline):
            captured["pipeline"] = pipeline
            return _Aggregate()

    monkeypatch.setattr(JobPosting, "get", staticmethod(get_job))
    monkeypatch.setattr(
        Application,
        "get_motor_collection",
        staticmethod(lambda: _Collection()),
    )
    app.dependency_overrides[get_current_recruiter] = lambda: recruiter
    try:
        response = client.get(
            f"/api/v1/jobs/{JOB_ID}/applications",
            params={"pipeline_status": "INTERVIEW", "min_ai_score": 78},
        )
        assert response.status_code == 200
        match_filter = captured["pipeline"][0]["$match"]
        assert str(match_filter["job_id"]) == JOB_ID
        assert match_filter["pipeline_status"] == "INTERVIEW"
        assert match_filter["ai_match_score"] == {"$gte": 78}
        assert captured["pipeline"][2]["$lookup"]["from"] == "users"
        assert captured["pipeline"][4]["$lookup"]["from"] == "skills_taxonomy"
        assert captured["pipeline"][5]["$lookup"]["from"] == "skills_taxonomy"
    finally:
        app.dependency_overrides.clear()


def test_list_ranked_job_applications_rejects_invalid_pipeline_status(client):
    recruiter = SimpleNamespace(id="64b000000000000000000020", user_type="RECRUITER")
    app.dependency_overrides[get_current_recruiter] = lambda: recruiter
    try:
        response = client.get(
            f"/api/v1/jobs/{JOB_ID}/applications",
            params={"pipeline_status": "UNKNOWN"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_get_my_cv_returns_pdf_or_404(client, monkeypatch, tmp_path):
    from app.services import cv_service

    monkeypatch.setattr(cv_service, "CV_DIR", tmp_path)
    user_dir = tmp_path / CANDIDATE_ID
    user_dir.mkdir(parents=True)
    pdf_file = user_dir / "mycv.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 sample cv")

    candidate = SimpleNamespace(
        id=CANDIDATE_ID,
        user_type="CANDIDATE",
        profile=SimpleNamespace(cv_url=f"/uploads/cvs/{CANDIDATE_ID}/mycv.pdf"),
    )
    app.dependency_overrides[get_current_candidate] = lambda: candidate
    try:
        response = client.get("/api/v1/users/me/cv")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-")

        candidate.profile.cv_url = None
        assert client.get("/api/v1/users/me/cv").status_code == 404
    finally:
        app.dependency_overrides.clear()
