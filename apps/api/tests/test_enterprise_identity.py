import hashlib

import pytest
from fastapi.testclient import TestClient

from apps.api.app.core.config import get_settings
from apps.api.app.core.errors import DatabaseWriteError
from apps.api.app.core.security import create_access_token
from apps.api.app.main import app
from apps.api.app.services.identity_service import IdentityService

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

    # 2. List Invitations: verify stored token is the SHA-256 hash, NOT raw secret
    expected_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    res_list = client.get("/api/v1/identity/invitations", headers=auth_headers)
    assert res_list.status_code == 200
    invitations = res_list.json()
    assert any(i["token"] == expected_hash for i in invitations)
    assert not any(i["token"] == token for i in invitations)

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


# =============================================================================
# 7. Members Directory & Status Management Tests
# =============================================================================

def test_organization_members_directory(auth_headers: dict[str, str], dev_headers: dict[str, str]) -> None:
    # 1. List members
    res = client.get("/api/v1/identity/members", headers=auth_headers)
    assert res.status_code == 200
    members = res.json()
    assert len(members) >= 1
    assert any(m["user_id"] == "usr_rahul" for m in members)

    # 2. Admin updates status
    res_patch = client.patch(
        "/api/v1/identity/members/usr_rahul/status",
        headers=auth_headers,
        json={"status": "SUSPENDED"},
    )
    assert res_patch.status_code == 200
    assert "SUSPENDED" in res_patch.json()["message"]

    # 3. Non-admin forbidden
    res_forbidden = client.patch(
        "/api/v1/identity/members/usr_rahul/status",
        headers=dev_headers,
        json={"status": "ACTIVE"},
    )
    assert res_forbidden.status_code == 403

    # 4. Non-existent member 404
    res_404 = client.patch(
        "/api/v1/identity/members/non_existent_user_id/status",
        headers=auth_headers,
        json={"status": "ACTIVE"},
    )
    assert res_404.status_code == 404


def test_device_edge_cases_and_resolver(auth_headers: dict[str, str], dev_headers: dict[str, str]) -> None:
    # 1. Revoke non-existent device returns 404
    res_404 = client.post("/api/v1/identity/devices/non_existent_device_id/revoke", headers=auth_headers)
    assert res_404.status_code == 404

    # 2. List external identities
    res_links = client.get("/api/v1/identity/links", headers=auth_headers)
    assert res_links.status_code == 200

    # 3. Resolve unknown user returns None
    assert IdentityService.resolve_canonical_user_id("snapmeet", "github", external_username="unknown_user_99999") is None
    assert IdentityService.resolve_canonical_user_id("snapmeet", "github", email="unknown_email@snapmeet.com") is None


def test_invitation_token_hashing_security(auth_headers: dict[str, str]) -> None:
    """
    P2.1 Acceptance Test:
    Ensures raw invitation token is never stored in plaintext in the database or memory store.
    Confirms acceptance fails with an invalid token and succeeds only with exact raw token.
    """
    inv = IdentityService.create_invitation(
        organization_id="snapmeet",
        email="security_test@snapmeet.com",
        name="Security Tester",
    )
    raw_token = inv.token
    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # Verify memory store stores the hash, not the raw token
    mem_invs = IdentityService._mem_invitations.get("snapmeet", [])
    matched_mem = next((i for i in mem_invs if i["email"] == "security_test@snapmeet.com"), None)
    assert matched_mem is not None
    assert matched_mem.get("token_hash") == expected_hash
    assert "token" not in matched_mem or matched_mem.get("token") != raw_token

    # Verify invalid token fails acceptance
    with pytest.raises(ValueError, match="Invalid or expired invitation token"):
        IdentityService.accept_invitation("invalid_token_123", "Tester", "Password123!")

    # Verify accepting with correct raw token succeeds
    accepted = IdentityService.accept_invitation(raw_token, "Tester", "Password123!")
    assert accepted["email"] == "security_test@snapmeet.com"


def test_identity_production_db_error_enforcement(monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    """
    P2.2 Acceptance Test:
    Ensures that when APP_ENV is 'production', any DB unavailability or write failure
    raises DatabaseWriteError (HTTP 500) rather than silently swallowing errors and falling back to memory.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "APP_ENV", "production")

    # Mock _safe_get_db to return None (database connection down)
    monkeypatch.setattr("apps.api.app.services.identity_service._safe_get_db", lambda: None)

    # Calling create_team in production with DB down MUST raise DatabaseWriteError
    with pytest.raises(DatabaseWriteError) as exc_info:
        IdentityService.create_team("snapmeet", "New Failing Team")
    assert "Database connection unavailable for create_team" in str(exc_info.value)

    # Calling create_invitation in production with DB down MUST raise DatabaseWriteError
    with pytest.raises(DatabaseWriteError) as exc_info:
        IdentityService.create_invitation("snapmeet", "failing@snapmeet.com")
    assert "Database connection unavailable for create_invitation" in str(exc_info.value)

    # Calling API endpoint returns HTTP 500
    res = client.post(
        "/api/v1/identity/teams",
        headers=auth_headers,
        json={"name": "Prod Failed Team"},
    )
    assert res.status_code == 500
    err_body = res.json()
    assert err_body["title"] == "DATABASE_WRITE_ERROR"

