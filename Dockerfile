###############################################################################
# Dockerfile — MONOLITH build for AgroScan NG.
#
# This is the DEFAULT Dockerfile used by the single Render service named
# "crop-detection".  One hostname serves EVERYTHING — both the React/Vite SPA
# frontend UI AND the Flask REST API — through a single nginx front-door on
# port 80, which is the only port Render Web Services expose publicly.
#
# Request routing (decided by nginx-monolith.conf):
#     /api/*            → proxied to gunicorn+Flask (bound to 127.0.0.1:5000,
#                         NOT reachable externally even on same Docker network)
#     /healthz          → proxied to /healthz on backend (so health check
#                         verifies both nginx and gunicorn are alive)
#     everything else   → served as Vite-built static SPA files, with a
#                         catch-all fallback to /index.html so React
#                         BrowserRouter deep-links work (/diagnose, /history)
#
# 3-stage build:
#   Stage 1 (builder-frontend) : node:20-alpine  →  npm install + vite build
#   Stage 2 (builder-backend)  : python:3.11-slim →  pip install backend deps
#   Stage 3 (runtime)          : python:3.11-slim + apt-install nginx/supervisor
#                                → COPY frontend dist/ from stage 1, backend /app
#                                from stage 2, start supervisord (runs both
#                                gunicorn + nginx)
#
# Render Dashboard UI settings for the single 'crop-detection' service:
#     Environment     = Docker
#     Dockerfile Path = Dockerfile        (← repo-root, this file)
#     Docker Context  = .
#     Health Check    = /healthz
#
# Optional Render env vars (safe to leave unset):
#     WEB_CONCURRENCY   = workers for gunicorn (Render auto-sets on free tier)
#     DATABASE_URL      = PostgreSQL connection string (falls back to SQLite)
#     INFERENCE_URL     = inference service URL (falls back to built-in dummy)
#     VITE_API_BASE_URL = baked at build time → automatically derives to same
#                         host '/api/v1' (see ARG below, so monolith works even
#                         without setting this env var in the UI)
#     ALLOWED_ORIGINS   = comma-separated list for CORS; defaults to wildcard
#                         '*' in monolith because frontend+api share origin
###############################################################################

# =============================================================================
# STAGE 1 / 3  —  Build Vite/React frontend
# =============================================================================
FROM node:20-alpine AS builder-frontend

WORKDIR /frontend

# Layer-cache: copy package files first (only re-runs npm install when
# package.json/package-lock.json change, not when source code changes)
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund

# Vite bakes any VITE_* env var into the static bundle at build time.
# For the MONOLITH we don't need an absolute URL — frontend and backend share
# the same origin, so we can use the relative path '/api/v1' and users never
# have to paste a Render hostname into the env. But still allow override via
# --build-arg VITE_API_BASE_URL=https://...  if needed for non-monolith tests.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY frontend ./
RUN npm run build

# =============================================================================
# STAGE 2 / 3  —  Install backend Python deps
# =============================================================================
FROM python:3.11-slim AS builder-backend

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copy repo root into /context then promote only api/ into /app — same
# context-agnostic trick used in api/Dockerfile so this stage works whether
# dockerContext is repo root OR ./api subdir (root is used here).
COPY . /context/
RUN set -eu; \
  if [ -f /context/api/requirements.txt ]; then \
    cp /context/api/requirements.txt /app/requirements.txt; \
    cp -rT /context/api /app_ctx_tmp_promote && rm -rf /app && mv /app_ctx_tmp_promote /app; \
  elif [ -f /context/requirements.txt ]; then \
    cp /context/requirements.txt /app/requirements.txt; \
  else \
    echo "requirements.txt missing in build context"; exit 1; \
  fi
RUN pip install --no-cache-dir -r /app/requirements.txt

# Directories needed by the backend (uploads) & make entrypoint executable
RUN mkdir -p /app/uploads/thumbnails && chmod +x /app/entrypoint.sh

# =============================================================================
# STAGE 3 / 3  —  RUNTIME: backend Python deps + nginx + SPA files + supervisord
# =============================================================================
FROM python:3.11-slim AS runtime

# Default WEB_CONCURRENCY — overridden by Render env var if present
ENV WEB_CONCURRENCY=2
ENV PYTHONUNBUFFERED=1

# 1) Install runtime packages:
#      - nginx        : front-door proxy + static SPA server
#      - supervisor   : runs (gunicorn + nginx) side-by-side under 1 supervisor
#      - curl         : health checks (gunicorn /api/v1/healthz, etc.)
# 2) Clean apt caches in same layer for small image.
RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx supervisor curl \
 && rm -rf /var/lib/apt/lists/* \
 && rm -f /etc/nginx/sites-enabled/default \
 && rm -f /etc/nginx/conf.d/default.conf

# Python packages (pre-installed site-packages from builder-backend) + /app tree
COPY --from=builder-backend /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder-backend /usr/local/bin /usr/local/bin
COPY --from=builder-backend /app /app

WORKDIR /app

# Monolith-optimised entrypoint runs migrations + seed ONLY on backend, does
# NOT start gunicorn (supervisor starts both gunicorn+nginx). Keep the same
# reliability properties as api/entrypoint.sh: tolerate seed failures.
RUN printf '%s\n' \
  '#!/bin/sh' \
  'set -eu' \
  'echo "[monolith-entry] Running database migrations..."' \
  'cd /app && alembic upgrade head' \
  'echo "[monolith-entry] Running seed (non-fatal on failure)..."' \
  'set +e; python seed.py; SEED_RC=$?; set -e' \
  'if [ "${SEED_RC}" -ne 0 ]; then' \
  '  echo "[monolith-entry][WARN] seed.py exited ${SEED_RC} — tolerating"' \
  'fi' \
  'echo "[monolith-entry] Starting supervisor (gunicorn + nginx)..."' \
  'exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf' \
  > /app/monolith-entrypoint.sh && chmod +x /app/monolith-entrypoint.sh

# Built Vite SPA static assets → nginx html directory
COPY --from=builder-frontend /frontend/dist /usr/share/nginx/html

# Routing rules: /api → gunicorn, / → SPA static + fallback
COPY nginx-monolith.conf /etc/nginx/conf.d/default.conf

# Supervisord configuration for (gunicorn + nginx) 2-process tree
COPY supervisord-monolith.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

# Monolith health check: curl through nginx to /healthz → which is reverse-
# proxied internally to backend /healthz.  Passing this health check proves
# both nginx AND gunicorn are running and reachable through the proxy.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=60s \
  CMD curl -f http://localhost/healthz || exit 1

ENTRYPOINT ["/app/monolith-entrypoint.sh"]
