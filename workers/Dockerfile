FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/ apps/api/
COPY packages/ packages/
COPY workers/ workers/

ENV PYTHONPATH="/"

CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info"]
