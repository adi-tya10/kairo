import pytest
from apps.api.app.core.security import create_access_token
from apps.api.app.main import app
from apps.api.app.services.identity_service import IdentityService
from fastapi.testclient import TestClient
from packages.schemas.identity import ExternalProvider, UserRole

client = TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token({
        "sub": "usr_snapmeet_admin",
        "org_id": "snapmeet",
        "email": "admin@snapmeet.com",
        "name": "SnapMeet Admin",
        "is_org_admin": True,
        "allowed_repos": ["snapmeet/billing-service", "snapmeet/auth-service"],
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def dev_headers() -> dict[str, str]:
    token = create_access_token({
        "sub": "usr_rahul",
        "org_id": "snapmeet",
        "email": "rahul@snapmeet.com",
        "name": "Rahul Sharma",
        "is_org_admin": False,
        "allowed_repos": ["snapmeet/billing-service"],
    })
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# 1. Teams API Tests
# =============================================================================

def test_teams_crud_flow(auth_headers: dict[str, str]) -> None:
    # 1. Create Team
    res = client.post(
        "/api/v1/identity/teams",
        headers=auth_headers,
        json={"name": "Core Platform", "description": "Infrastructure and billing pods"},
    )
    assert res.status_code == 201
    team_data = res.json()
    assert team_data["name"] == "Core Platform"
    team_id = team_data["id"]

    # 2. Add Member to Team
    res_add = client.post(
        f"/api/v1/identity/teams/{team_id}/members",
        headers=auth_headers,
        json={"user_id": "usr_rahul"},
    )
    assert res_add.status_code == 200

    # 3. List Teams
    res_list = client.get("/api/v1/identity/teams", headers=auth_headers)
    assert res_list.status_code == 200
    teams = res_list.json()
    assert any(t["name"] == "Core Platform" for t in teams)


# =============================================================================
# 2. Invitations Lifecycle Tests
# =============================================================================

def test_invitation_lifecycle(auth_headers: dict[str, str]) -> None:
    # 1. Admin sends invitation
    res_inv = client.post(
        "/api/v1/identity/invitations",
        headers=auth_headers,
        json={
            "email": "priya@snapmeet.com",
            "name": "Priya Patel",
            "role": "DEVELOPER",
            "allowed_repos": ["snapmeet/billing-service"],
        },
    )
    assert res_inv.status_code == 201
    inv_data = res_inv.json()
    assert inv_data["email"] == "priya@snapmeet.com"
    token = inv_data["token"]

    # 2. List Invitations
    res_list = client.get("/api/v1/identity/invitations", headers=auth_headers)
    assert res_list.status_code == 200
    assert any(i["token"] == token for i in res_list.json())

    # 3. Employee accepts invitation
    res_accept = client.post(
        "/api/v1/identity/invitations/accept",
        json={
            "token": token,
            "name": "Priya Patel",
            "password": "PriyaPassword2026!",
        },
    )
    assert res_accept.status_code == 200
    accept_data = res_accept.json()
    assert "access_token" in accept_data
    assert accept_data["user"]["email"] == "priya@snapmeet.com"

    # 4. Re-accepting should fail (single-use token)
    res_repeat = client.post(
        "/api/v1/identity/invitations/accept",
        json={
            "token": token,
            "name": "Priya Patel",
            "password": "PriyaPassword2026!",
        },
    )
    assert res_repeat.status_code == 400


# =============================================================================
# 3. Device Enrollment & Revocation Tests
# =============================================================================

def test_device_enrollment_and_revocation(dev_headers: dict[str, str], auth_headers: dict[str, str]) -> None:
    # 1. Enroll device
    res_enroll = client.post(
        "/api/v1/identity/devices/enroll",
        headers=dev_headers,
        json={
            "device_name": "Rahul-ThinkPad-T14",
            "platform": "windows",
            "app_version": "2.0.0",
        },
    )
    assert res_enroll.status_code == 201
    dev_data = res_enroll.json()
    assert dev_data["device_name"] == "Rahul-ThinkPad-T14"
    assert dev_data["status"] == "ACTIVE"
    device_id = dev_data["id"]

    # 2. List Devices
    res_list = client.get("/api/v1/identity/devices", headers=dev_headers)
    assert res_list.status_code == 200
    assert any(d["id"] == device_id for d in res_list.json())

    # 3. Revoke Device
    res_revoke = client.post(
        f"/api/v1/identity/devices/{device_id}/revoke",
        headers=auth_headers,
    )
    assert res_revoke.status_code == 200
    assert not IdentityService.is_device_active("snapmeet", device_id)


# =============================================================================
# 4. Cross-Tool Identity Resolver & Linking Tests
# =============================================================================

def test_cross_tool_identity_resolver(auth_headers: dict[str, str]) -> None:
    # 1. Link external GitHub and Jira handles to Rahul
    res_link = client.post(
        "/api/v1/identity/links",
        headers=auth_headers,
        json={
            "user_id": "usr_rahul",
            "provider": "github",
            "external_user_id": "gh_89412",
            "external_username": "rahul-dev",
            "external_email": "rahul@snapmeet.com",
        },
    )
    assert res_link.status_code == 201

    client.post(
        "/api/v1/identity/links",
        headers=auth_headers,
        json={
            "user_id": "usr_rahul",
            "provider": "jira",
            "external_user_id": "7120:38194",
            "external_username": "Rahul Jira",
            "external_email": "rahul@snapmeet.com",
        },
    )

    # 2. Resolve Canonical user_id from GitHub username
    resolved_gh = IdentityService.resolve_canonical_user_id(
        organization_id="snapmeet",
        provider="github",
        external_username="rahul-dev",
    )
    assert resolved_gh == "usr_rahul"

    # 3. Resolve Canonical user_id from Jira account ID
    resolved_jira = IdentityService.resolve_canonical_user_id(
        organization_id="snapmeet",
        provider="jira",
        external_user_id="7120:38194",
    )
    assert resolved_jira == "usr_rahul"

    # 4. Resolve Canonical user_id via email matching fallback
    resolved_email = IdentityService.resolve_canonical_user_id(
        organization_id="snapmeet",
        provider="linear",
        email="admin@snapmeet.com",
    )
    assert resolved_email == "usr_snapmeet_admin"


# =============================================================================
# 5. Full Authorized Identity Context (/me/context)
# =============================================================================

def test_user_identity_context_endpoint(dev_headers: dict[str, str]) -> None:
    res = client.get("/api/v1/me/context", headers=dev_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "usr_rahul"
    assert data["organization_id"] == "snapmeet"
    assert "teams" in data
    assert "devices" in data
    assert "external_identities" in data


# =============================================================================
# 6. Deep Link Authorization Code Exchange Test
# =============================================================================

def test_auth_code_deep_link_exchange(dev_headers: dict[str, str]) -> None:
    # 1. Generate one-time code
    res_code = client.post("/api/v1/identity/auth/device-code", headers=dev_headers)
    assert res_code.status_code == 200
    code = res_code.json()["code"]

    # 2. Exchange one-time code for JWT session
    res_exchange = client.post("/api/v1/identity/auth/exchange-code", json={"code": code})
    assert res_exchange.status_code == 200
    assert "access_token" in res_exchange.json()

    # 3. Second exchange fails
    res_fail = client.post("/api/v1/identity/auth/exchange-code", json={"code": code})
    assert res_fail.status_code == 400
