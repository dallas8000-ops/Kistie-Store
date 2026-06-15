# Kistie Store on Railway — basic setup

## Your Django app (unchanged)

Railway does **not** edit your repo. The app was always:

| Piece | Location |
|-------|----------|
| Django project | `backend/` |
| `manage.py` | `backend/manage.py` |
| WSGI | `backend/core/wsgi.py` → `core.wsgi:application` |
| Dependencies | `requirements.txt` (repo root) |

That matches **`render.yaml`** (the original deploy spec):

```yaml
startCommand: gunicorn --chdir backend core.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

## What went wrong (not a Django bug)

Railway’s default builder **Railpack** assumes a flat Python app (`app.py` / `main.py` at repo root).  
Your Django app lives in **`backend/`**, so Railpack ran the wrong start command and crashed.

Extra files (`app.py`, `main.py`, root `manage.py`, etc.) were **workarounds** added in git — they were not part of the original app and piled on confusion.

**This repo now uses one path only: the `Dockerfile`** (same idea as `render.yaml`).

## Railway dashboard (do once)

### 1. Source
- Repo: `dallas8000-ops/Kistie-Store`
- Branch: `main`
- **Root directory:** empty (repo root)

### 2. Build
- **Builder:** `Dockerfile` (not Railpack)
- **Dockerfile path:** `Dockerfile`

If deploy logs say `railpack-plan.json` or `python app.py`, the builder is still wrong or you **Redeployed an old artifact** — trigger a **new** deploy from GitHub instead.

### 3. Deploy
- **Custom start command:** **empty** (Dockerfile `CMD` runs `scripts/railway-start.sh`)

### 4. Variables (minimum)

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `DJANGO_SECRET_KEY` | long random string |
| `DJANGO_DEBUG` | `False` |
| `ALLOWED_HOSTS` | `.railway.app kistie-store-production.up.railway.app` |
| `SITE_URL` | `https://kistie-store-production.up.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://kistie-store-production.up.railway.app` |

Do **not** set `PORT` — Railway injects it.

### 5. Deploy fresh (critical)

**Deployments → Deploy from GitHub** (latest `main`).  
Do **not** use “Redeploy” on an old deployment — that reuses a broken Railpack image.

A good build log starts with: `load build definition from Dockerfile`  
A good runtime log shows: `Starting Kistie Store (PORT=8080)...` then gunicorn listening.

### 6. Verify

`https://kistie-store-production.up.railway.app/health/?format=json`  
→ `{"status":"ok","service":"kistie-store"}`
