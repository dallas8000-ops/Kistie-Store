#!/bin/sh
set -e
python backend/manage.py migrate --noinput
exec gunicorn --chdir backend core.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120
