import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "kairo_workers",
    broker=REDIS_URL,
    backend=None,
    include=[
        "workers.tasks.ingest",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=True,  # Executes in-process when broker is offline
    task_eager_propagates=True,
    broker_connection_retry_on_startup=False,
    task_routes={
        "workers.tasks.ingest.*": {"queue": "ingest"},
    },
)
