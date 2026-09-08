import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
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
        "workers.tasks.embeddings.*": {"queue": "embeddings"},
        "workers.tasks.alerts.*": {"queue": "alerts"},
        "workers.tasks.diagram.*": {"queue": "diagram"},
    },
)
