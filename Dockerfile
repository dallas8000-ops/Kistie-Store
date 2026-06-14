FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SECRET_KEY=build-placeholder-not-used-at-runtime
ENV DJANGO_DEBUG=False

RUN python backend/manage.py collectstatic --noinput

EXPOSE 8080

CMD ["sh", "-c", "python backend/manage.py migrate --noinput && (python backend/manage.py seed_inventory_if_empty || true) && (python backend/manage.py link_static_images_to_products || true) && exec gunicorn --chdir backend core.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120"]
