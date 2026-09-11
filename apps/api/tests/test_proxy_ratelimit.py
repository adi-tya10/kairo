"""
Unit tests for secure reverse proxy IP handling and production fail-closed behavior.
Verifies that untrusted clients cannot spoof client IPs via X-Forwarded-For,
trusted reverse proxies are properly unwound, and production database failures fail closed.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers

from apps.api.app.core.network import get_client_ip


def make_mock_request(client_host: str | None, x_forwarded_for: str | None = None):
    req = MagicMock()
    if client_host is not None:
        req.client = MagicMock(host=client_host)
    else:
        req.client = None

    headers_dict = {}
    if x_forwarded_for is not None:
        headers_dict["x-forwarded-for"] = x_forwarded_for

    req.headers = Headers(headers_dict)
    return req


def test_direct_client_without_proxy() -> None:
    req = make_mock_request("198.51.100.55")
    ip = get_client_ip(req, trusted_proxies=["127.0.0.1", "::1"])
    assert ip == "198.51.100.55"


def test_untrusted_client_cannot_spoof_x_forwarded_for() -> None:
    # Direct client is 198.51.100.55 (untrusted) claiming to be 8.8.8.8
    req = make_mock_request("198.51.100.55", x_forwarded_for="8.8.8.8")
    ip = get_client_ip(req, trusted_proxies=["127.0.0.1", "::1"])
    # MUST return the actual socket IP, ignoring spoofed header
    assert ip == "198.51.100.55"


def test_trusted_proxy_single_forwarded_ip() -> None:
    # Reverse proxy is 127.0.0.1 (trusted) forwarding real client 203.0.113.195
    req = make_mock_request("127.0.0.1", x_forwarded_for="203.0.113.195")
    ip = get_client_ip(req, trusted_proxies=["127.0.0.1", "::1"])
    assert ip == "203.0.113.195"


def test_trusted_proxy_chain_with_intermediate_proxy() -> None:
    # Client 203.0.113.50 passed through internal proxies
    req = make_mock_request("127.0.0.1", x_forwarded_for="203.0.113.50, 10.0.0.1, 127.0.0.1")
    ip = get_client_ip(req, trusted_proxies=["127.0.0.1", "10.0.0.1", "::1"])
    assert ip == "203.0.113.50"


def test_trusted_proxy_with_empty_or_whitespace_header() -> None:
    req = make_mock_request("127.0.0.1", x_forwarded_for="   ,   ")
    ip = get_client_ip(req, trusted_proxies=["127.0.0.1"])
    assert ip == "127.0.0.1"


def test_client_none_safely_handled() -> None:
    req = make_mock_request(None)
    ip = get_client_ip(req)
    assert ip == "unknown"


@pytest.mark.asyncio
async def test_production_auth_db_failure_fails_closed() -> None:
    """Verifies that in production mode, DB failure raises 503 instead of falling back to memory."""
    from apps.api.app.api.v1.auth import login_user, LoginRequest
    from apps.api.app.core.config import get_settings

    mock_db = MagicMock()
    mock_db.table.side_effect = RuntimeError("Supabase connection refused")
    req = make_mock_request("127.0.0.1")
    login_req = LoginRequest(email="admin@testcorp.com", password="SecurePassword123!")

    settings = get_settings()
    with patch.object(settings, "APP_ENV", "production"):
        with pytest.raises(HTTPException) as exc_info:
            await login_user(login_req, req, mock_db)
        assert exc_info.value.status_code == 503
        assert "temporarily unavailable" in exc_info.value.detail.lower()
