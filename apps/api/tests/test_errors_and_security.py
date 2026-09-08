import hashlib
import hmac
from unittest.mock import MagicMock

import pytest
from fastapi import Request

from apps.api.app.core.config import get_settings
from apps.api.app.core.errors import (
    AccessRestrictedError,
    SignatureVerificationError,
    TenantIsolationError,
    kairo_exception_handler,
)
from apps.api.app.core.security import (
    create_access_token,
    decode_access_token,
    verify_github_signature,
)


def test_custom_errors():
    err1 = TenantIsolationError()
    assert err1.error_code == "TENANT_ISOLATION_VIOLATION"
    assert err1.status_code == 403

    err2 = AccessRestrictedError()
    assert err2.error_code == "ACCESS_RESTRICTED"
    assert err2.status_code == 403

    err3 = SignatureVerificationError()
    assert err3.error_code == "INVALID_SIGNATURE"
    assert err3.status_code == 401


@pytest.mark.asyncio
async def test_kairo_exception_handler():
    mock_request = MagicMock(spec=Request)
    mock_request.url = "https://api.kairo.dev/test"

    exc = TenantIsolationError("Unauthorized tenant query")
    response = await kairo_exception_handler(mock_request, exc)
    assert response.status_code == 403

    generic_exc = ValueError("Unexpected system failure")
    response_generic = await kairo_exception_handler(mock_request, generic_exc)
    assert response_generic.status_code == 500


def test_jwt_token_flow():
    data = {"sub": "usr_aman", "org_id": "org_snapmeet", "allowed_repos": ["snapmeet/billing-service"]}
    token = create_access_token(data)
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert decoded["sub"] == "usr_aman"
    assert decoded["org_id"] == "org_snapmeet"
    assert "snapmeet/billing-service" in decoded["allowed_repos"]


def test_github_signature_verification_success():
    payload = b'{"action": "opened", "number": 88}'
    settings = get_settings()
    secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")
    valid_sig = "sha256=" + hmac.new(secret, payload, hashlib.sha256).hexdigest()

    assert verify_github_signature(payload, valid_sig) is True


def test_github_signature_verification_failure():
    payload = b'{"action": "opened", "number": 88}'
    invalid_sig = "sha256=invalid_hex_digest_123456"

    with pytest.raises(SignatureVerificationError):
        verify_github_signature(payload, invalid_sig)


def test_github_signature_verification_missing():
    payload = b'{"action": "opened", "number": 88}'
    with pytest.raises(SignatureVerificationError):
        verify_github_signature(payload, None)


def test_production_configuration_fail_fast():
    """Confirms production mode fails loudly if insecure/default credentials or wildcard CORS are used."""
    from apps.api.app.core.config import Settings

    # 1. Insecure default SECRET_KEY in production
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            APP_ENV="production",
            SECRET_KEY="kairo-development-secret-key-change-in-production",
            SUPABASE_URL="https://test.supabase.co",
            SUPABASE_SERVICE_ROLE_KEY="valid-test-key-for-prod",
            NEO4J_URI="bolt://localhost:7687",
            NEO4J_USER="neo4j",
            NEO4J_PASSWORD="secure_prod_password_123",
        )

    # 2. Wildcard CORS in production
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(
            APP_ENV="production",
            SECRET_KEY="a_very_long_cryptographically_secure_random_key_32_chars",
            CORS_ORIGINS=["*"],
            SUPABASE_URL="https://test.supabase.co",
            SUPABASE_SERVICE_ROLE_KEY="valid-test-key-for-prod",
            NEO4J_URI="bolt://localhost:7687",
            NEO4J_USER="neo4j",
            NEO4J_PASSWORD="secure_prod_password_123",
        )

    # 3. Missing Supabase credentials in production
    with pytest.raises(ValueError, match="SUPABASE_URL"):
        Settings(
            APP_ENV="production",
            SECRET_KEY="a_very_long_cryptographically_secure_random_key_32_chars",
            SUPABASE_URL="",
            SUPABASE_SERVICE_ROLE_KEY="",
        )

