# Production Dockerfile for EpiSense Epidemiological Surveillance Backend
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8008 \
    HOST=0.0.0.0 \
    EPISENSE_DB_PATH=/var/data/surveillance_store.sqlite

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and reference datasets
COPY src/ /app/src/
COPY data/ /app/data/
COPY run_server.py /app/run_server.py
COPY configs/ /app/configs/

# Create persistent storage mount directory
RUN mkdir -p /var/data

EXPOSE 8008

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/v1/health || exit 1

CMD ["python", "run_server.py"]
