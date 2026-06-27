# syntax=docker/dockerfile:1.4
# ─────────────────────────────────────────────────────────────────────────────
# Multi-stage build — optimized with BuildKit cache mounts
# BUILD_ENV: production (default) | development
# ─────────────────────────────────────────────────────────────────────────────
ARG BUILD_ENV=production

# ── Builder Stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ARG BUILD_ENV=production
WORKDIR /tmp

# Build dependencies (gcc/build-essential only needed for compiled wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements_local.txt ./

# Cache pip downloads between builds via BuildKit mount
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    if [ "${BUILD_ENV}" = "development" ]; then \
      pip wheel --wheel-dir /tmp/wheels -r requirements_local.txt; \
    else \
      pip wheel --wheel-dir /tmp/wheels -r requirements.txt; \
    fi

# ── Runtime Stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

ARG BUILD_ENV=production
WORKDIR /app

# Minimal runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pre-built wheels (fast, no compilation)
COPY --from=builder /tmp/wheels /wheels
COPY requirements.txt requirements_local.txt ./

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    if [ "${BUILD_ENV}" = "development" ]; then \
      pip install --no-index --find-links /wheels -r requirements_local.txt || \
      pip install --find-links /wheels -r requirements_local.txt; \
    else \
      pip install --no-index --find-links /wheels -r requirements.txt || \
      pip install --find-links /wheels -r requirements.txt; \
    fi && \
    rm -rf /wheels

# Application code
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
