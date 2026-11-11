from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app
from app.models.application import Application
from app.models.company import Company
from app.models.job import JobPosting
from app.models.user import User


class _Query:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self):
        return self.rows


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_admin_statistics_requires_admin_role(client):
    assert client.get("/api/v1/admin/statistics").status_code == 401

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="u1", role="USER", user_type="CANDIDATE", status="ACTIVE"
    )
    assert client.get("/api/v1/admin/statistics").status_code == 403

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="u2", role="USER", user_type="RECRUITER", status="ACTIVE"
    )
    assert client.get("/api/v1/admin/statistics").status_code == 403


def test_admin_statistics_aggregates_all_metrics(client, monkeypatch):
    users = [
        SimpleNamespace(role="ADMIN", user_type=None, status="ACTIVE", deleted_at=None),
        SimpleNamespace(role="USER", user_type="CANDIDATE", status="ACTIVE", deleted_at=None),
        SimpleNamespace(role="USER", user_type="CANDIDATE", status="BANNED", deleted_at=None),
        SimpleNamespace(role="USER", user_type="RECRUITER", status="ACTIVE", deleted_at=None),
    ]
    companies = [
        SimpleNamespace(verification_status="PENDING", deleted_at=None),
        SimpleNamespace(verification_status="VERIFIED", deleted_at=None),
        SimpleNamespace(verification_status="VERIFIED", deleted_at=None),
        SimpleNamespace(verification_status="REJECTED", deleted_at=None),
    ]
    jobs = [
        SimpleNamespace(status="OPEN", deleted_at=None),
        SimpleNamespace(status="OPEN", deleted_at=None),
        SimpleNamespace(status="CLOSED", deleted_at=None),
        SimpleNamespace(status="HIDDEN", deleted_at=None),
    ]
    applications = [
        SimpleNamespace(
            pipeline_status="APPLIED",
            ai_match_score=49.9,
            matching_version="v1.0",
            ai_status="DONE",
        ),
        SimpleNamespace(
            pipeline_status="SCREENING",
            ai_match_score=50.0,
            matching_version="v1.0",
            ai_status="DONE",
        ),
        SimpleNamespace(
            pipeline_status="INTERVIEW",
            ai_match_score=75.0,
            matching_version="v2.0",
            ai_status="DONE",
        ),
        SimpleNamespace(
            pipeline_status="HIRED",
            ai_match_score=85.1,
            matching_version="v2.0",
            ai_status="COMPLETED",
        ),
        SimpleNamespace(
            pipeline_status="REJECTED",
            ai_match_score=None,
            matching_version="v1.0",
            ai_status="FAILED",
        ),
    ]

    monkeypatch.setattr(User, "find", staticmethod(lambda _flt: _Query(users)))
    monkeypatch.setattr(Company, "find", staticmethod(lambda _flt: _Query(companies)))
    monkeypatch.setattr(JobPosting, "find", staticmethod(lambda _flt: _Query(jobs)))
    monkeypatch.setattr(Application, "find_all", staticmethod(lambda: _Query(applications)))

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="admin-1", role="ADMIN", user_type=None, status="ACTIVE"
    )

    response = client.get("/api/v1/admin/statistics")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["users"]["total"] == 4
    assert data["users"]["candidates"] == 2
    assert data["users"]["recruiters"] == 1
    assert data["users"]["admins"] == 1
    assert data["users"]["active"] == 3
    assert data["users"]["banned"] == 1

    assert data["companies"]["total"] == 4
    assert data["companies"]["pending"] == 1
    assert data["companies"]["verified"] == 2
    assert data["companies"]["rejected"] == 1

    assert data["jobs"]["total"] == 4
    assert data["jobs"]["open"] == 2
    assert data["jobs"]["closed"] == 1
    assert data["jobs"]["hidden"] == 1

    assert data["applications"]["total"] == 5
    assert data["applications"]["by_pipeline_status"] == {
        "APPLIED": 1,
        "SCREENING": 1,
        "INTERVIEW": 1,
        "HIRED": 1,
        "REJECTED": 1,
    }

    ai = data["ai_matching"]
    assert ai["total_scored"] == 4
    assert ai["average_score"] == 65.0
    assert ai["score_distribution"]["under_50"] == 1
    assert ai["score_distribution"]["from_50_to_75"] == 2
    assert ai["score_distribution"]["over_75"] == 1
    assert ai["score_distribution"]["<50%"] == 1
    assert ai["score_distribution"]["50-75%"] == 2
    assert ai["score_distribution"][">75%"] == 1
    assert ai["by_matching_version"] == {"v1.0": 3, "v2.0": 2}
    assert ai["by_ai_status"]["DONE"] == 4
    assert ai["by_ai_status"]["FAILED"] == 1
