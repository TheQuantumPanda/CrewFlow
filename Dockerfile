# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the React SPA.
# Node is only needed to produce static files, so it never reaches the runtime
# image. That keeps the deployed container to Python plus the built assets.
# ---------------------------------------------------------------------------
FROM node:20-alpine AS web

WORKDIR /web

# Copy the manifests first so `npm ci` is only re-run when dependencies
# actually change, not on every source edit.
COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build


# ---------------------------------------------------------------------------
# Stage 2 — the Python runtime.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production

WORKDIR /app

# libpq is needed by psycopg; curl backs the container HEALTHCHECK below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=web /web/dist ./web/dist

# Run as an unprivileged user — a process that never needs to write to the
# image should not be able to.
RUN useradd --create-home --uid 10001 taskforge \
    && chown -R taskforge:taskforge /app
USER taskforge

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/healthz" || exit 1

# Shell form so ${PORT} is expanded — managed hosts inject the port at runtime.
CMD gunicorn \
    --chdir backend \
    --config backend/gunicorn.conf.py \
    --bind "0.0.0.0:${PORT:-8000}" \
    "task_management:create_app()"
