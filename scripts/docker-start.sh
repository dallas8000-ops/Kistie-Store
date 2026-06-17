#!/bin/sh
set -e
echo "[kistie-store] migrate..."
python backend/manage.py migrate --noinput || echo "[kistie-store] WARN: migrate failed — starting gunicorn anyway"
PORT="${PORT:-8080}"
echo "[kistie-store] gunicorn on 0.0.0.0:${PORT}"
exec gunicorn --chdir backend core.wsgi:application --bind "0.0.0.0:${PORT}" --workers 2 --timeout 120 --access-logfile - --error-logfile -
