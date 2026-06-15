web: python backend/manage.py migrate --noinput && gunicorn --chdir backend core.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
