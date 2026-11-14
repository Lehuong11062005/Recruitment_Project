from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app
from app.models.user import CandidateProfile, User
from app.services import profile_service

EXPORT_URL = "/api/v1/users/me/profile/export-pdf"
USER_ID = PydanticObjectId("64b000000000000000000001")
PYTHON_ID = PydanticObjectId("64b000000000000000000002")
REACT_ID = PydanticObjectId("64b000000000000000000003")
MISSING_ID = PydanticObjectId("64b000000000000000000004")


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


def test_export_resolves_own_skills_and_returns_pdf(client, monkeypatch):
    candidate = SimpleNamespace(
        id=USER_ID, user_type="CANDIDATE", email="candidate@example.com",
        full_name="Nguyễn Đỗ Thị Ánh Tuyết", phone=None,
        profile=CandidateProfile(skills=[PYTHON_ID, MISSING_ID, REACT_ID, PYTHON_ID]),
    )
    app.dependency_overrides[get_current_user] = lambda: candidate

    class UserCollection:
        def aggregate(self, stages):
            assert stages[0] == {"$match": {"_id": USER_ID}}
            return self

        async def to_list(self, length):
            assert length == 1
            return [{"export_skills": [
                {"_id": REACT_ID, "name": "React"},
                {"_id": PYTHON_ID, "name": "Python"},
            ]}]

    monkeypatch.setattr(User, "get_motor_collection", UserCollection)
    render_profile_pdf = profile_service.render_profile_pdf

    def render(profile, skill_names):
        assert profile.full_name == candidate.full_name
        assert skill_names == ["Python", "React"]
        return render_profile_pdf(profile, skill_names)

    monkeypatch.setattr(profile_service, "render_profile_pdf", render)
    response = client.get(EXPORT_URL)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="ho-so-ung-vien.pdf"'
    assert response.headers["cache-control"] == "private, no-store"
    assert response.content.startswith(b"%PDF-")


def test_export_requires_candidate_role(client):
    assert client.get(EXPORT_URL).status_code == 401

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_type="RECRUITER")
    assert client.get(EXPORT_URL).status_code == 403


def test_export_supports_candidate_without_saved_profile(client):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=USER_ID, user_type="CANDIDATE", email="candidate@example.com",
        full_name="Ứng viên", phone=None, profile=None,
    )

    response = client.get(EXPORT_URL)

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
