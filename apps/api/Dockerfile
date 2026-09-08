FROM python:3.11-slim

WORKDIR /app

# Install git and system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and packages
COPY apps/api/ apps/api/
COPY packages/ packages/
COPY workers/ workers/

# Make start script executable
COPY apps/api/start.sh /app/start.sh
RUN chmod +x /app/start.sh

ENV PYTHONPATH="/app"
EXPOSE 8000

CMD ["/app/start.sh"]
