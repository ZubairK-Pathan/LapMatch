# ==========================================
# Stage 1: Base - Setup runtime environment
# ==========================================
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Copy runtime requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Test - Run linter and tests
# ==========================================
FROM base AS test

# Copy development requirements and install them
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy config files, source code, and tests
COPY pyproject.toml .
COPY app.py .
COPY models/ ./models/
COPY data/ ./data/
COPY static/ ./static/
COPY tests/ ./tests/

# Run Ruff linter and formatter checks, then Pytest
RUN ruff check . && \
    ruff format --check . && \
    pytest

# ==========================================
# Stage 3: Production - Final minimal image
# ==========================================
FROM base AS production

# Copy runtime application files only
COPY app.py .
COPY models/ ./models/
COPY data/ ./data/
COPY static/ ./static/

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
