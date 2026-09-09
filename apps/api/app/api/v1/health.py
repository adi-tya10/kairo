from fastapi import APIRouter, status
from pydantic import BaseModel

from apps.api.app.core.database import (
    check_database_health,
    check_neo4j_health,
    check_redis_health,
)

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    postgresql: bool
    neo4j_graph: bool
    redis: bool


@router.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check covering PostgreSQL (Supabase), Neo4j AuraDB, and Redis.
    Returns overall status as 'healthy' only when all dependencies are reachable.
    Returns 'degraded' with individual flags when one or more services are down.
    """
    pg_ok = await check_database_health()
    neo4j_ok = await check_neo4j_health()
    redis_ok = await check_redis_health()

    overall = "healthy" if (pg_ok and neo4j_ok and redis_ok) else "degraded"

    return HealthResponse(
        status=overall,
        service="kairo-api",
        version="0.1.0",
        postgresql=pg_ok,
        neo4j_graph=neo4j_ok,
        redis=redis_ok,
    )
