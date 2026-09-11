import os
import ssl
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from celery import Celery
from dotenv import load_dotenv

ROOT_ENV = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ROOT_ENV)
load_dotenv()


def _ensure_ssl_params(url: str) -> str:
    """Ensures rediss:// URLs have ssl_cert_reqs set for Celery RedisBackend compatibility."""
    if not url:
        return url
    if url.startswith("rediss://"):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if "ssl_cert_reqs" not in query:
            query["ssl_cert_reqs"] = ["CERT_NONE"]
            new_query = urlencode(query, doseq=True)
            return urlunparse(parsed._replace(query=new_query))
    return url


REDIS_URL = _ensure_ssl_params(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
CELERY_BROKER_URL = _ensure_ssl_params(os.environ.get("CELERY_BROKER_URL", REDIS_URL))
CELERY_RESULT_BACKEND = _ensure_ssl_params(os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL))
TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "false").lower() in ("true", "1")
WORKER_CONCURRENCY = int(os.environ.get("CELERY_CONCURRENCY", "4"))

celery_app = Celery(
    "kairo_workers",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "workers.tasks.ingest",
        "workers.tasks.embeddings",
        "workers.tasks.alerts",
        "workers.tasks.diagram",
        "workers.tasks.slack_task",
        "workers.tasks.backfill_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    worker_concurrency=WORKER_CONCURRENCY,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    result_expires=86400,  # 24 hours TTL: prevents unbounded Redis RAM growth
    broker_transport_options={"visibility_timeout": 43200},  # 12 hours for long jobs
    task_routes={
        "workers.tasks.ingest.*": {"queue": "ingest"},
        "workers.tasks.slack_task.*": {"queue": "ingest"},
        "workers.tasks.backfill_task.*": {"queue": "ingest"},
        "workers.tasks.embeddings.*": {"queue": "embeddings"},
        "workers.tasks.alerts.*": {"queue": "alerts"},
        "workers.tasks.diagram.*": {"queue": "diagram"},
    },
)

if "rediss://" in CELERY_BROKER_URL or "rediss://" in CELERY_RESULT_BACKEND:
    celery_app.conf.update(
        broker_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
        redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
    )

