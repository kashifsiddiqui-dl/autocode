# =============================================================================
# Auto Code Backend - Development Dockerfile
# =============================================================================

FROM python:3.12-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required by lxml, psycopg2, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specification and install
COPY backend/pyproject.toml backend/pyproject.toml
RUN pip install -e "./backend[dev]" 2>/dev/null || pip install -r backend/requirements.txt 2>/dev/null || echo "Install from pyproject.toml"

# Install the project in editable mode if pyproject.toml exists
RUN cd backend && pip install -e ".[dev]" 2>/dev/null || true

# Copy application code
COPY backend/ backend/

WORKDIR /app/backend

EXPOSE 8000

# Development server with hot reload
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
