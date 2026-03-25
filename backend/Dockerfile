# Multi-stage build for both development and production
# Build arg: BUILD_ENV determines if we use local (dev) or production requirements
ARG BUILD_ENV=production

# ===== Builder Stage =====
FROM python:3.11-slim as builder

ARG BUILD_ENV=production
WORKDIR /tmp

# Install build dependencies (only in builder stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy appropriate requirements based on environment
COPY requirements.txt requirements_local.txt ./

RUN if [ "${BUILD_ENV}" = "development" ]; then \
      pip wheel --no-cache-dir --no-deps --wheel-dir /tmp/wheels -r requirements_local.txt; \
    else \
      pip wheel --no-cache-dir --no-deps --wheel-dir /tmp/wheels -r requirements.txt; \
    fi

# ===== Runtime Stage =====
FROM python:3.11-slim

ARG BUILD_ENV=production
WORKDIR /app

# Install runtime dependencies only (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install
COPY --from=builder /tmp/wheels /wheels
COPY requirements.txt requirements_local.txt ./

RUN if [ "${BUILD_ENV}" = "development" ]; then \
      pip install --no-cache /wheels/* && \
      pip install -r requirements_local.txt 2>/dev/null || true; \
    else \
      pip install --no-cache /wheels/* && \
      pip install -r requirements.txt 2>/dev/null || true; \
    fi && \
    rm -rf /wheels

# Copy application code
COPY . .

EXPOSE 8000

# Health check
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]