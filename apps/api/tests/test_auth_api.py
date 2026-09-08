import uuid
from fastapi.testclient import TestClient

from apps.api.app.main import app

client = TestClient(app)


def test_auth_registration_and_login_flow() -> None:
    test_id = uuid.uuid4().hex[:8]
    test_email = f"admin_{test_id}@acmecorp.io"

    # 1. Register new organization
    reg_payload = {
        "company_name": f"Acme Corp {test_id}",
        "admin_email": test_email,
        "password": "SecurePassword2026!",
        "plan_tier": "ENTERPRISE",
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert "access_token" in data
    assert data["company_name"] == f"Acme Corp {test_id}"
    assert data["is_org_admin"] is True

    # 2. Login with registered credentials
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": "SecurePassword2026!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # 3. Test /me profile verification
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    profile = me_res.json()
    assert profile["email"] == test_email


def test_auth_login_invalid_credentials() -> None:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@snapmeet.com", "password": "WrongPassword!"},
    )
    assert res.status_code == 401
