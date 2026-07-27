#!/bin/sh
# entrypoint.sh — AgroScan-API container boot script.
# Flow:
#   1. Print DB connectivity diagnostics (useful for debugging Render env-var pickup)
#   2. Run alembic migrations (idempotent)
#   3. Run DB seed (idempotent, and seed.py now NEVER exits non-zero)
#   4. Start gunicorn wsgi server
#
# Safety properties:
#   - Only step 1 and 2 can fail the deploy (gunicorn must start unless DB is unreachable).
#   - Step 3 errors are tolerated (deploy proceeds; seed can be re-applied later).
set -e

echo "[entrypoint] ──────────────────────────────────────────────"
echo "[entrypoint] AgroScan-API starting..."
echo "[entrypoint] CWD            : $(pwd)"
echo "[entrypoint] WORKDIR (/app) : $(ls -la /app 2>/dev/null | head -5)"
echo "[entrypoint] DATABASE_URL   : ${DATABASE_URL:-<NOT SET> (will FALLBACK to sqlite:///dev.db)}"
echo "[entrypoint] INFERENCE_URL  : ${INFERENCE_URL:-<NOT SET>}"
echo "[entrypoint] ALLOWED_ORIGINS: ${ALLOWED_ORIGINS:-<NOT SET>}"
echo "[entrypoint] ──────────────────────────────────────────────"

if [ -z "${DATABASE_URL}" ]; then
  echo "[entrypoint][WARN] ========================================="
  echo "[entrypoint][WARN] DATABASE_URL env var is NOT SET!"
  echo "[entrypoint][WARN] App will use SQLite fallback (sqlite:///dev.db)"
  echo "[entrypoint][WARN] In Render Dashboard -> agroscan-api -> Environment:"
  echo "[entrypoint][WARN]   Key   = DATABASE_URL"
  echo "[entrypoint][WARN]   Value = <internal Render PostgreSQL connection string>"
  echo "[entrypoint][WARN]   (or use Blueprint Sync if services were created from render.yaml)"
  echo "[entrypoint][WARN] ========================================="
fi

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Running seed (skipped if data already exists; never fatal)..."
# NOTE: seed.py already wraps everything in try/except and forces sys.exit(0),
# but we also do NOT run under set -e for this specific command to be robust.
set +e
python seed.py
SEED_RC=$?
set -e
if [ "${SEED_RC}" -ne 0 ]; then
  echo "[entrypoint][WARN] seed.py exited ${SEED_RC} — tolerating and proceeding to boot (seed can be re-run later)."
fi

echo "[entrypoint] Starting gunicorn..."
echo "[entrypoint] WEB_CONCURRENCY=${WEB_CONCURRENCY:-<auto by gunicorn>}"
exec gunicorn --bind 0.0.0.0:5000 --workers ${WEB_CONCURRENCY:-2} --timeout 120 wsgi:app
