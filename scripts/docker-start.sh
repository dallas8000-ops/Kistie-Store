#!/bin/sh
set -e
PORT="${PORT:-8080}"
echo "[kistie-store] PORT=${PORT}"
echo "[kistie-store] loading Django..."
python backend/manage.py check --deploy || echo "[kistie-store] WARN: deploy check reported issues (starting anyway)"
echo "[kistie-store] running migrations..."
python backend/manage.py migrate --noinput || echo "[kistie-store] WARN: migrate failed (starting anyway)"
echo "[kistie-store] starting gunicorn on 0.0.0.0:${PORT}"
exec gunicorn --chdir backend core.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
