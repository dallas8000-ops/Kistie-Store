# Kistie Store — Railway deploy

Production runs on **Railway** (Dockerfile + PostgreSQL).

## Find the right service

Railway does **not** name it “Kistie Store web”. You need the service whose **Source** is repo **`Kistie-Store`** (not the Postgres box).

If only Postgres exists → **+ New → GitHub Repo → Kistie-Store**.

## Variables (on the Kistie-Store repo service only)

| Name | Value |
|------|--------|
| `DJANGO_SECRET_KEY` | long random string (copy from local `backend/.env` — **not** deployed automatically) |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` — pick your Postgres service from the reference menu |
| `ALLOWED_HOSTS` | `.railway.app .up.railway.app kistie-store-production.up.railway.app healthcheck.railway.app` |
| `SITE_URL` | `https://kistie-store-production.up.railway.app` (or your custom domain) |
| `CONTACT_RECIPIENT_EMAIL` | Gmail inbox for contact-form inquiries |
| `DJANGO_EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` (for real Gmail delivery) |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USE_TLS` | `smtp.gmail.com` / `587` / `True` |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `DJANGO_DEFAULT_FROM_EMAIL` | Gmail + app password |

Do **not** paste `DATABASE_URL` twice on one line. Do **not** set `PORT`.

## Build

- Builder: **Dockerfile** (from `railway.toml`)
- Custom start command: **empty** (image `CMD` / `Procfile` handles start)

## Deploy

**Deploy latest commit** from GitHub — not **Redeploy** on an old deployment.

Good build log: `load build definition from Dockerfile`  
Good runtime log: `[kistie-store] gunicorn on 0.0.0.0:8080`

## Verify

- Health: `https://kistie-store-production.up.railway.app/health/?format=json` → `{"status":"ok","service":"kistie-store"}`
- Contact: submit `/contact/` → inquiry appears in Django admin **and** (with SMTP vars) arrives at `CONTACT_RECIPIENT_EMAIL`
