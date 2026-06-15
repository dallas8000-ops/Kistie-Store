# Kristie Store on Railway

Django app lives in **`backend/`** (`manage.py`, `core.wsgi`). Do **not** use Railway’s default `python app.py` start.

## Fix “Application failed to respond” (502)

### 1. Railway → kistie-store → **Settings → Deploy**

- **Custom Start Command:** must be **completely empty**. If it says `python app.py || python main.py`, delete it — that forces a start path that ignores `railpack.json` / `Procfile`.
- **Redeploy** after every push to `main`; confirm the deployment shows commit **`ac3a624`** or newer (not an older SHA).
- Add variable **`RAILPACK_START_CMD`** (highest priority for Railpack):

  ```
  python backend/manage.py migrate --noinput && python -m gunicorn core.wsgi:application --chdir backend --bind 0.0.0.0:$PORT --workers 2 --timeout 120
  ```### 2. **Settings → Networking**

- **Target port:** **8080** on your public domain (Railway injects `PORT=8080`; gunicorn binds `0.0.0.0:$PORT`).
- If the domain shows target port **3000** or **8000**, change it to **8080** — wrong target port causes 502 “Application failed to respond”.
- Do **not** set a custom **Start Command** in the UI; the repo `Dockerfile` runs `scripts/railway-start.sh`.

### 3. **Variables** (Raw Editor)

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `DJANGO_SECRET_KEY` | long random string |
| `DJANGO_DEBUG` | `False` |
| `ALLOWED_HOSTS` | `.railway.app kistie-store-production.up.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://kistie-store-production.up.railway.app` |
| `RAILPACK_START_CMD` | `sh scripts/railway-start.sh` (optional; fixes Railpack if deploy still runs `python app.py`) |

### 4. Redeploy

After push to `main`, trigger **Deploy** → wait for build logs to show `gunicorn`, not `app.py`.

### 5. Verify

- https://kistie-store-production.up.railway.app/health/?format=json  
  Expected: `{"status":"ok","service":"kistie-store"}`

**Note:** Service hostname is **`kistie-store`** (typo), not `kristie-store`.
