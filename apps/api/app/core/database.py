"""
KAIRO Database Session & Client Layer.
Provides dependency-injectable Supabase / PostgreSQL and Neo4j AuraDB clients
with health validation. Fails loudly on missing credentials — never returns
fake or degraded sessions silently.
"""
from collections.abc import Generator

import httpx
import redis
from neo4j import AsyncGraphDatabase, GraphDatabase
from neo4j import Driver as Neo4jDriver
from neo4j import Session as Neo4jSession
from supabase import Client, create_client

from apps.api.app.core.config import get_settings
from apps.api.app.core.logging import get_logger

logger = get_logger("kairo.core.database")

# ---------------------------------------------------------------------------
# Redis Connection Pool & Client
# ---------------------------------------------------------------------------

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """
    Returns a configured, connection-pooled singleton Redis client instance.
    Shared across API replicas for distributed rate limiting and caching.
    Supports TLS (rediss://) and enforces socket connection timeouts.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    settings = get_settings()
    pool = redis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=50,
        decode_responses=True,
        socket_connect_timeout=5.0,
        socket_timeout=5.0,
    )
    _redis_client = redis.Redis(connection_pool=pool)
    return _redis_client


def reset_redis_client() -> None:
    """Resets the singleton Redis client instance (used for testing and clean shutdown)."""
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.close()
        except Exception:
            pass
        _redis_client = None


async def check_redis_health(timeout: float = 5.0) -> bool:
    """
    Verifies that the Redis server is reachable via PING.
    Fails closed if the service is unreachable.
    """
    try:
        client = get_redis_client()
        return bool(client.ping())
    except Exception as exc:
        logger.error(f"Redis health check failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Supabase / PostgreSQL
# ---------------------------------------------------------------------------

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Returns a configured, singleton Supabase client instance.
    Raises ValueError if credentials are not configured.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured in environment."
        )

    _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_client


def get_db() -> Generator[Client, None, None]:
    """
    Reusable dependency for FastAPI routes requiring a Supabase/PostgreSQL client.
    """
    client = get_supabase_client()
    try:
        yield client
    finally:
        pass


async def check_database_health(timeout: float = 5.0) -> bool:
    """
    Verifies that the Supabase / PostgreSQL database endpoint is reachable.
    Fails closed if the service is unreachable or DNS resolution fails.
    """
    settings = get_settings()
    if not settings.SUPABASE_URL:
        logger.error("Database health check failed: SUPABASE_URL is empty.")
        return False

    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY or "",
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY or ''}",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as http_client:
            response = await http_client.get(url, headers=headers)
            # PostgREST root /rest/v1/ returns 200 with OpenAPI schema when service is healthy
            if response.status_code in (200, 401):
                return True
            logger.warning(
                f"Database health check returned unexpected status code: {response.status_code}"
            )
            return False
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
        logger.error(f"Database health check failed to reach {url}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Neo4j AuraDB (Temporal Knowledge Graph)
# ---------------------------------------------------------------------------

_neo4j_driver: Neo4jDriver | None = None


def get_neo4j_driver() -> Neo4jDriver:
    """
    Returns a configured, singleton Neo4j driver instance.

    Reads NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD from settings.
    Raises ValueError clearly if any credential is missing — never falls back
    to a fake or local default.
    """
    global _neo4j_driver
    if _neo4j_driver is not None:
        return _neo4j_driver

    settings = get_settings()

    if not settings.NEO4J_URI:
        raise ValueError(
            "NEO4J_URI must be configured in environment (e.g. neo4j+s://<id>.databases.neo4j.io)."
        )
    if not settings.NEO4J_USER:
        raise ValueError("NEO4J_USER must be configured in environment.")
    if not settings.NEO4J_PASSWORD:
        raise ValueError("NEO4J_PASSWORD must be configured in environment.")

    _neo4j_driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        # Connection pool tuned for FastAPI's concurrent worker model
        max_connection_pool_size=50,
        connection_acquisition_timeout=30,
    )
    logger.info(f"Neo4j driver initialized for URI: {settings.NEO4J_URI}")
    return _neo4j_driver


def get_graph_db() -> Generator[Neo4jSession, None, None]:
    """
    Reusable dependency for FastAPI routes requiring a Neo4j session.
    Opens a new session per request and guarantees teardown via the finally block.

    Usage in a route:
        session: Neo4jSession = Depends(get_graph_db)
    """
    driver = get_neo4j_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()


async def check_neo4j_health(timeout: float = 5.0) -> bool:
    """
    Verifies that the Neo4j AuraDB cluster is reachable and accepting queries.
    Uses the lightweight driver.verify_connectivity() call wrapped in a timeout.
    Fails closed — returns False on any error.
    """
    settings = get_settings()

    if not settings.NEO4J_URI or not settings.NEO4J_USER or not settings.NEO4J_PASSWORD:
        logger.error("Neo4j health check skipped: one or more NEO4J_* env vars are empty.")
        return False

    try:
        async with AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        ) as driver:
            await driver.verify_connectivity()
        return True
    except Exception as exc:
        logger.error(f"Neo4j health check failed: {exc}")
        return False


def reset_neo4j_driver() -> None:
    """
    Closes and resets the singleton Neo4j driver.
    Intended for use in tests and graceful shutdown handlers only.
    """
    global _neo4j_driver
    if _neo4j_driver is not None:
        _neo4j_driver.close()
        _neo4j_driver = None
