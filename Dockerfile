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

RUN chmod +x scripts/railway-start.sh

EXPOSE 8080

CMD ["/app/scripts/railway-start.sh"]
