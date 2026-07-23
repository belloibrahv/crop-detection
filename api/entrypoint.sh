#!/bin/sh
# entrypoint.sh — runs DB migrations and seeds on first boot, then starts gunicorn.
# Safe to run on every container restart: alembic is idempotent, seed checks
# for existing data before inserting.
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Running seed (skipped if data already exists)..."
python seed.py

echo "[entrypoint] Starting gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 wsgi:app
