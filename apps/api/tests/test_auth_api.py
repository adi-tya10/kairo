import uuid

import pytest
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


def test_distributed_rate_limiter_shared_across_instances() -> None:
    """
    Validates that rate limit state is shared across multiple API replicas/instances
    via a shared Redis client, preventing distributed brute-force attacks.
    """
    from fastapi import HTTPException

    from apps.api.app.api.v1.auth import _check_rate_limit

    class MockRedisPipeline:
        def __init__(self, store: dict[str, list[float]]) -> None:
            self.store = store
            self.key = ""
            self.items: list[tuple[str, float]] = []

        def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> "MockRedisPipeline":
            self.key = key
            if key in self.store:
                self.store[key] = [s for s in self.store[key] if s > max_score]
            return self

        def zadd(self, key: str, mapping: dict[str, float]) -> "MockRedisPipeline":
            self.key = key
            entries = self.store.setdefault(key, [])
            for _, score in mapping.items():
                entries.append(score)
            return self

        def zcard(self, key: str) -> "MockRedisPipeline":
            return self

        def expire(self, key: str, ttl: int) -> "MockRedisPipeline":
            return self

        def execute(self) -> list[int]:
            count = len(self.store.get(self.key, []))
            return [0, len(self.items), count, 1]

    class MockSharedRedis:
        def __init__(self) -> None:
            # Single shared backend store (simulates Redis cluster)
            self.store: dict[str, list[float]] = {}

        def pipeline(self) -> MockRedisPipeline:
            return MockRedisPipeline(self.store)

    shared_redis = MockSharedRedis()
    client_ip = f"198.51.100.{uuid.uuid4().hex[:4]}"

    # Simulate Instance A handling 10 attempts
    for _ in range(10):
        _check_rate_limit(client_ip, redis_client=shared_redis)

    # Simulate Instance B handling 10 attempts
    for _ in range(10):
        _check_rate_limit(client_ip, redis_client=shared_redis)

    # Instance A receives the 21st attempt -> must be blocked by shared Redis state
    import pytest
    with pytest.raises(HTTPException) as exc_info:
        _check_rate_limit(client_ip, redis_client=shared_redis)
    assert exc_info.value.status_code == 429
    assert "Too many authentication attempts" in str(exc_info.value.detail)


def test_rate_limiter_memory_fallback() -> None:
    """Verifies that the rate limiter gracefully falls back to memory if Redis is unavailable."""
    import pytest
    from fastapi import HTTPException

    from apps.api.app.api.v1.auth import MAX_AUTH_ATTEMPTS, _check_rate_limit

    client_id = f"test_mem_{uuid.uuid4().hex[:6]}"
    for _ in range(MAX_AUTH_ATTEMPTS):
        _check_rate_limit(client_id, redis_client=None)

    with pytest.raises(HTTPException) as exc_info:
        _check_rate_limit(client_id, redis_client=None)
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_redis_health_and_client() -> None:
    from unittest.mock import MagicMock, patch

    from apps.api.app.core.database import check_redis_health

    mock_client = MagicMock()
    mock_client.ping.return_value = True

    with patch("apps.api.app.core.database.get_redis_client", return_value=mock_client):
        healthy = await check_redis_health()
        assert healthy is True

    with patch("apps.api.app.core.database.get_redis_client", side_effect=Exception("Redis down")):
        unhealthy = await check_redis_health()
        assert unhealthy is False


