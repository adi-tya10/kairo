import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI

from apps.api.app.core.config import get_settings
from apps.api.app.core.database import (
    check_database_health,
    check_neo4j_health,
    check_redis_health,
    get_db,
    get_graph_db,
    get_neo4j_driver,
    get_redis_client,
    get_supabase_client,
    reset_neo4j_driver,
    reset_redis_client,
)
from apps.api.app.core.logging import JSONFormatter
from apps.api.app.main import lifespan

# ---------------------------------------------------------------------------
# Supabase / PostgreSQL tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_database_health_success():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        is_healthy = await check_database_health(timeout=1.0)
        assert is_healthy is True


@pytest.mark.asyncio
async def test_check_database_health_connection_failure():
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("DNS error")):
        is_healthy = await check_database_health(timeout=1.0)
        assert is_healthy is False


@pytest.mark.asyncio
async def test_check_database_health_empty_url():
    settings = get_settings()
    with patch.object(settings, "SUPABASE_URL", ""):
        is_healthy = await check_database_health(timeout=1.0)
        assert is_healthy is False


def test_get_supabase_client_unconfigured():
    settings = get_settings()
    with (
        patch("apps.api.app.core.database._supabase_client", None),
        patch.object(settings, "SUPABASE_URL", ""),
        pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured"),
    ):
        get_supabase_client()


def test_get_supabase_client_and_dependency():
    settings = get_settings()
    with (
        patch("apps.api.app.core.database._supabase_client", None),
        patch.object(settings, "SUPABASE_URL", "https://mock.supabase.co"),
        patch.object(settings, "SUPABASE_SERVICE_ROLE_KEY", "mock_key"),
        patch("apps.api.app.core.database.create_client") as mock_create,
    ):
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        client = get_supabase_client()
        assert client == mock_client

        gen = get_db()
        yielded = next(gen)
        assert yielded == mock_client


@pytest.mark.asyncio
async def test_lifespan_production_failure():
    settings = get_settings()
    test_app = FastAPI()
    with (
        patch("apps.api.app.main.check_database_health", return_value=False),
        patch.object(settings, "APP_ENV", "production"),
        pytest.raises(RuntimeError, match="Production startup failure"),
    ):
        async with lifespan(test_app):
            pass


@pytest.mark.asyncio
async def test_check_database_health_unexpected_status():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response

        is_healthy = await check_database_health(timeout=1.0)
        assert is_healthy is False


@pytest.mark.asyncio
async def test_lifespan_development_warning():
    settings = get_settings()
    test_app = FastAPI()
    with (
        patch("apps.api.app.main.check_database_health", return_value=False),
        patch.object(settings, "APP_ENV", "development"),
    ):
        async with lifespan(test_app):
            pass


def test_logging_json_formatter_with_extra_fields():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test.py",
        lineno=10,
        msg="Sample error",
        args=(),
        exc_info=None,
    )
    record.organization_id = "org_123"
    record.request_id = "req_456"
    try:
        raise ValueError("test exception")
    except ValueError:
        import sys
        record.exc_info = sys.exc_info()

    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["organization_id"] == "org_123"
    assert parsed["request_id"] == "req_456"
    assert "test exception" in parsed["exception"]


# ---------------------------------------------------------------------------
# Neo4j driver unit tests
# ---------------------------------------------------------------------------

def test_get_neo4j_driver_raises_when_uri_missing():
    """get_neo4j_driver() raises ValueError when NEO4J_URI is empty."""
    settings = get_settings()
    reset_neo4j_driver()
    with (
        patch("apps.api.app.core.database._neo4j_driver", None),
        patch.object(settings, "NEO4J_URI", ""),
        pytest.raises(ValueError, match="NEO4J_URI must be configured"),
    ):
        get_neo4j_driver()
    reset_neo4j_driver()


def test_get_neo4j_driver_raises_when_user_missing():
    """get_neo4j_driver() raises ValueError when NEO4J_USER is empty."""
    settings = get_settings()
    reset_neo4j_driver()
    with (
        patch("apps.api.app.core.database._neo4j_driver", None),
        patch.object(settings, "NEO4J_URI", "neo4j+s://test.databases.neo4j.io"),
        patch.object(settings, "NEO4J_USER", ""),
        pytest.raises(ValueError, match="NEO4J_USER must be configured"),
    ):
        get_neo4j_driver()
    reset_neo4j_driver()


def test_get_neo4j_driver_raises_when_password_missing():
    """get_neo4j_driver() raises ValueError when NEO4J_PASSWORD is empty."""
    settings = get_settings()
    reset_neo4j_driver()
    with (
        patch("apps.api.app.core.database._neo4j_driver", None),
        patch.object(settings, "NEO4J_URI", "neo4j+s://test.databases.neo4j.io"),
        patch.object(settings, "NEO4J_USER", "neo4j"),
        patch.object(settings, "NEO4J_PASSWORD", ""),
        pytest.raises(ValueError, match="NEO4J_PASSWORD must be configured"),
    ):
        get_neo4j_driver()
    reset_neo4j_driver()


def test_get_neo4j_driver_creates_and_caches_driver():
    """get_neo4j_driver() creates driver on first call and returns same instance thereafter."""
    settings = get_settings()
    reset_neo4j_driver()
    mock_driver = MagicMock()

    with (
        patch("apps.api.app.core.database._neo4j_driver", None),
        patch.object(settings, "NEO4J_URI", "neo4j+s://test.databases.neo4j.io"),
        patch.object(settings, "NEO4J_USER", "neo4j"),
        patch.object(settings, "NEO4J_PASSWORD", "secret"),
        patch("apps.api.app.core.database.GraphDatabase.driver", return_value=mock_driver),
    ):
        driver_1 = get_neo4j_driver()
        driver_2 = get_neo4j_driver()

    assert driver_1 is driver_2
    assert driver_1 is mock_driver
    reset_neo4j_driver()


def test_get_graph_db_yields_session_and_closes():
    """get_graph_db() yields a session and closes it on generator teardown."""
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session

    with patch("apps.api.app.core.database.get_neo4j_driver", return_value=mock_driver):
        gen = get_graph_db()
        yielded = next(gen)
        assert yielded is mock_session

        # Advance past the finally block
        try:
            next(gen)
        except StopIteration:
            pass

        mock_session.close.assert_called_once()


def test_reset_neo4j_driver_closes_and_clears():
    """reset_neo4j_driver() calls close() on the driver and sets singleton to None."""
    import apps.api.app.core.database as db_module

    mock_driver = MagicMock()
    db_module._neo4j_driver = mock_driver

    reset_neo4j_driver()

    assert db_module._neo4j_driver is None
    mock_driver.close.assert_called_once()


@pytest.mark.asyncio
async def test_check_neo4j_health_missing_credentials():
    """check_neo4j_health() returns False when NEO4J_URI is empty — does not hang or raise."""
    settings = get_settings()
    with patch.object(settings, "NEO4J_URI", ""):
        result = await check_neo4j_health(timeout=1.0)
    assert result is False


@pytest.mark.asyncio
async def test_check_neo4j_health_connection_failure():
    """check_neo4j_health() returns False on connectivity failure — never raises to caller."""
    mock_driver_instance = AsyncMock()
    mock_driver_instance.verify_connectivity = AsyncMock(side_effect=Exception("connection refused"))
    mock_driver_instance.__aenter__ = AsyncMock(return_value=mock_driver_instance)
    mock_driver_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("apps.api.app.core.database.AsyncGraphDatabase.driver", return_value=mock_driver_instance):
        result = await check_neo4j_health(timeout=1.0)

    assert result is False


def test_settings_production_validation() -> None:
    """Verifies fail-fast production security guardrails in Settings."""
    from apps.api.app.core.config import Settings

    valid_prod_kwargs = {
        "_env_file": None,
        "APP_ENV": "production",
        "SECRET_KEY": "a" * 32,
        "CORS_ORIGINS": ["https://app.kairo.dev"],
        "SUPABASE_URL": "https://prod.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "secure_supabase_role_key_prod",
        "NEO4J_URI": "neo4j+s://prod.databases.neo4j.io",
        "NEO4J_USER": "prod_neo4j",
        "NEO4J_PASSWORD": "super_secure_prod_password",
        "REDIS_URL": "rediss://prod.redis.io:6379/0",
        "GITHUB_WEBHOOK_SECRET": "prod_sec_github_987654321",
        "JIRA_WEBHOOK_SECRET": "prod_sec_jira_987654321",
        "LINEAR_WEBHOOK_SECRET": "prod_sec_linear_987654321",
        "GITLAB_WEBHOOK_SECRET": "prod_sec_gitlab_987654321",
    }

    # Valid production settings pass
    settings = Settings(**valid_prod_kwargs)
    assert settings.APP_ENV == "production"

    # Insecure secret key
    with pytest.raises(ValueError, match="SECRET_KEY must be a cryptographically secure"):
        Settings(**{**valid_prod_kwargs, "SECRET_KEY": "short"})

    # Wildcard CORS
    with pytest.raises(ValueError, match="Wildcard"):
        Settings(**{**valid_prod_kwargs, "CORS_ORIGINS": ["*"]})

    # Missing Supabase
    with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required"):
        Settings(**{**valid_prod_kwargs, "SUPABASE_URL": ""})

    # Missing Neo4j
    with pytest.raises(ValueError, match="NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD are required"):
        Settings(**{**valid_prod_kwargs, "NEO4J_PASSWORD": ""})

    # Default Neo4j password
    with pytest.raises(ValueError, match="Insecure default NEO4J_PASSWORD"):
        Settings(**{**valid_prod_kwargs, "NEO4J_PASSWORD": "kairo_password"})

    # Missing Redis
    with pytest.raises(ValueError, match="REDIS_URL is required"):
        Settings(**{**valid_prod_kwargs, "REDIS_URL": ""})

    # Default webhook secrets
    with pytest.raises(ValueError, match="Default GITHUB_WEBHOOK_SECRET"):
        Settings(**{**valid_prod_kwargs, "GITHUB_WEBHOOK_SECRET": "kairo_github_webhook_secret_local"})

    with pytest.raises(ValueError, match="Default JIRA_WEBHOOK_SECRET"):
        Settings(**{**valid_prod_kwargs, "JIRA_WEBHOOK_SECRET": "kairo_jira_webhook_secret_local"})

    with pytest.raises(ValueError, match="Default LINEAR_WEBHOOK_SECRET"):
        Settings(**{**valid_prod_kwargs, "LINEAR_WEBHOOK_SECRET": "kairo_linear_webhook_secret_local"})

    with pytest.raises(ValueError, match="Default GITLAB_WEBHOOK_SECRET"):
        Settings(**{**valid_prod_kwargs, "GITLAB_WEBHOOK_SECRET": "kairo_gitlab_webhook_secret_local"})


# ---------------------------------------------------------------------------
# Redis tests
# ---------------------------------------------------------------------------

def test_get_redis_client_unconfigured():
    settings = get_settings()
    reset_redis_client()
    with patch.object(settings, "REDIS_URL", ""):
        with pytest.raises(ValueError, match="REDIS_URL must be configured"):
            get_redis_client()
    reset_redis_client()


def test_get_redis_client_and_reset():
    settings = get_settings()
    reset_redis_client()
    with (
        patch.object(settings, "REDIS_URL", "redis://localhost:6379/0"),
        patch("redis.ConnectionPool.from_url") as mock_pool,
        patch("redis.Redis") as mock_redis,
    ):
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        c1 = get_redis_client()
        c2 = get_redis_client()
        assert c1 is c2
        assert mock_pool.call_count == 1
        assert mock_redis.call_count == 1

        reset_redis_client()
        mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_check_redis_health_success():
    with patch("apps.api.app.core.database.get_redis_client") as mock_get:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_get.return_value = mock_client

        healthy = await check_redis_health()
        assert healthy is True


@pytest.mark.asyncio
async def test_check_redis_health_failure():
    with patch("apps.api.app.core.database.get_redis_client") as mock_get:
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("Redis down")
        mock_get.return_value = mock_client

        healthy = await check_redis_health()
        assert healthy is False

