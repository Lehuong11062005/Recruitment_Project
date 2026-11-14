from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app

ADMIN_ID = PydanticObjectId("64b000000000000000000001")
RECORD_ID = "64b000000000000000000002"


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize(("method", "path", "body"), [
    ("GET", "/users", None),
    ("GET", "/companies", None),
    ("GET", "/jobs", None),
    ("PATCH", f"/users/{RECORD_ID}/status", {"status": "BANNED"}),
    ("PATCH", f"/companies/{RECORD_ID}/verify", {"verification_status": "VERIFIED"}),
    ("PATCH", f"/jobs/{RECORD_ID}/status", {"status": "DELETED"}),
])
def test_admin_moderation_requires_admin(client, method, path, body):
    url = "/api/v1/admin" + path
    assert client.request(method, url, json=body).status_code == 401

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="USER")
    assert client.request(method, url, json=body).status_code == 403


def test_admin_cannot_lock_current_account(client):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="ADMIN", id=ADMIN_ID)
    response = client.patch(f"/api/v1/admin/users/{ADMIN_ID}/status", json={"status": "BANNED"})
    assert response.status_code == 409
