from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.api.v1.health import router as health_router
from apps.api.app.api.v1.router import api_v1_router
from apps.api.app.core.config import get_settings
from apps.api.app.core.database import (
    check_database_health,
    check_neo4j_health,
    check_redis_health,
)
from apps.api.app.core.errors import KairoError, kairo_exception_handler
from apps.api.app.core.logging import get_logger

logger = get_logger("kairo.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Comprehensive Startup Infrastructure Health Checks
    logger.info(f"Starting {settings.APP_NAME} in environment: {settings.APP_ENV}")
    db_healthy = await check_database_health()
    redis_healthy = await check_redis_health()
    neo4j_healthy = await check_neo4j_health()

    if not db_healthy:
        if settings.APP_ENV == "production":
            logger.critical("FATAL: Database health check failed in production! Host unreachable.")
            raise RuntimeError("Production startup failure: Database health check failed.")
        else:
            logger.warning("Database is unreachable; continuing in development mode.")

    if not redis_healthy:
        logger.warning(
            "Redis is unreachable at startup; distributed rate limiter and Celery tasks running in fallback mode."
        )

    if not neo4j_healthy:
        logger.warning(
            "Neo4j AuraDB is unreachable at startup; graph operations will operate in circuit-breaker mode."
        )

    yield
    logger.info("Shutting down KAIRO API server.")


app = FastAPI(
    title=settings.APP_NAME,
    description="KAIRO Work Continuity & Temporal Knowledge Engine Gateway",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.onrender\.com|http://localhost:\d+|http://127\.0\.0\.1:\d+|tauri://localhost",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(KairoError, kairo_exception_handler)

# Include v1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
app.include_router(health_router)  # Root level /health convenience mount


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "engine": "KAIRO Work Continuity Engine",
        "status": "operational",
        "docs": "/docs",
    }
