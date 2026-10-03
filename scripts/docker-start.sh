#!/bin/sh
set -e
echo "[kistie-store] migrate..."
python backend/manage.py migrate --noinput
echo "[kistie-store] seed inventory (no-op if already populated)..."
python backend/manage.py seed_inventory_if_empty
echo "[kistie-store] link catalog images..."
python backend/manage.py link_static_images_to_products
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "[kistie-store] ensure admin account (skipped if it exists)..."
  python backend/manage.py createsuperuser --noinput --email "${DJANGO_SUPERUSER_EMAIL:-}" 2>&1 || echo "[kistie-store] admin already exists or could not be created"
fi
PORT="${PORT:-8080}"
echo "[kistie-store] gunicorn on 0.0.0.0:${PORT}"
exec gunicorn --chdir backend core.wsgi:application --bind "0.0.0.0:${PORT}" --workers 2 --timeout 120 --access-logfile - --error-logfile -
