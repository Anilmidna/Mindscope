#!/bin/sh
# ECS container startup: run DB migrations then start the API server.
# Alembic is idempotent — safe to run on every container start.
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
