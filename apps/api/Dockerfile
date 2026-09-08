FROM python:3.11-slim

WORKDIR /app

# Install git and system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and packages
COPY apps/api/ apps/api/
COPY packages/ packages/
COPY workers/ workers/

ENV PYTHONPATH="/"
EXPOSE 8000

CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
