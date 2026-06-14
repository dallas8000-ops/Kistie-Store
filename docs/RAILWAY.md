# Kristie Store on Railway

Kristie Store is a **Django** app (`backend/manage.py`, `core.wsgi`). Railway must **not** use the default Python start (`python app.py` / `python main.py`).

This repo ships:

- `Procfile` + `railway.toml` → `gunicorn --chdir backend core.wsgi:application`
- `scripts/railway-start.sh` → migrate, seed, then gunicorn

## Railway service: `kistie-store-production`

### Required variables

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `DJANGO_SECRET_KEY` | long random string |
| `DJANGO_DEBUG` | `False` |
| `ALLOWED_HOSTS` | `.railway.app kistie-store-production.up.railway.app` |
| `SITE_URL` | `https://kistie-store-production.up.railway.app` |

### Networking

Set the public port to match **`PORT`** (usually **8080** on Railway).

### After deploy

- Health: `https://kistie-store-production.up.railway.app/health/`
- Portfolio live demo links to this hostname (typo `kistie` vs `kristie`).
