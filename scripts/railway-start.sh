#!/bin/sh
set -e
cd "$(dirname "$0")/.."
echo "Starting Kistie Store (PORT=${PORT:-8080})..."
python backend/manage.py migrate --noinput
python backend/manage.py seed_inventory_if_empty || true
python backend/manage.py link_static_images_to_products || true
exec gunicorn --chdir backend core.wsgi:application \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers 2 \
  --timeout 120
