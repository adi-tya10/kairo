#!/bin/sh
set -e

PORT_TO_BIND="${PORT:-8000}"
echo "========================================================"
echo "  KAIRO Enterprise Gateway - Starting on Port ${PORT_TO_BIND}"
echo "========================================================"

# Launch Celery background worker if REDIS_URL is configured
if [ -n "$REDIS_URL" ]; then
    echo "[+] Initializing background Celery worker (Concurrency: 1)..."
    export C_FORCE_ROOT=1
    celery -A workers.celery_app worker --loglevel=info --concurrency=1 &
else
    echo "[!] REDIS_URL not detected. Running without background worker."
fi

echo "[+] Launching FastAPI Gateway with Uvicorn..."
exec uvicorn apps.api.app.main:app --host 0.0.0.0 --port "${PORT_TO_BIND}"
