# Railway production image — Kistie Store
# manage.py: backend/manage.py
# WSGI: core.wsgi:application (gunicorn --chdir backend)
# Port: ${PORT:-8080}

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

RUN DJANGO_SECRET_KEY=build-placeholder-not-used-at-runtime \
    DJANGO_DEBUG=False \
    python backend/manage.py collectstatic --noinput

EXPOSE 8080

# Matches root Procfile (same level as requirements.txt)
CMD ["sh", "-c", "python backend/manage.py migrate --noinput && exec gunicorn --chdir backend core.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120"]
