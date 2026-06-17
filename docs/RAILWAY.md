# Kistie Store — go live (pick one)

## Option A: Render (simplest — already configured)

The repo includes **`render.yaml`**. Render knows this is Django in `backend/` — no Dockerfile fights.

1. [render.com](https://render.com) → **New** → **Blueprint** → connect `dallas8000-ops/Kistie-Store`
2. Approve the blueprint (web + Postgres). Render auto-sets `DJANGO_SECRET_KEY` and `DATABASE_URL`.
3. Add your email secrets in the dashboard if you use contact form SMTP.
4. URL will be like `https://kristie-store.onrender.com` — update `SITE_URL` / DNS when ready.

Health: `/health/?format=json` → `{"status":"ok","service":"kistie-store"}`

---

## Option B: Railway

### Find the right service

Railway does **not** name it “Kistie Store web”. You need the service whose **Source** is repo **`Kistie-Store`** (not the Postgres box).

If only Postgres exists → **+ New → GitHub Repo → Kistie-Store**.

### Variables (on the Kistie-Store repo service only)

| Name | Value |
|------|--------|
| `DJANGO_SECRET_KEY` | long random string (copy from local `backend/.env` — **not** deployed automatically) |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` — pick your Postgres service from the reference menu |
| `ALLOWED_HOSTS` | `.railway.app .up.railway.app kistie-store-production.up.railway.app healthcheck.railway.app` |

Do **not** paste `DATABASE_URL` twice on one line. Do **not** set `PORT`.

### Build

- Builder: **Dockerfile** (from `railway.toml`)
- Custom start command: **empty**

### Deploy

**Deploy latest commit** from GitHub — not **Redeploy** on an old deployment.

Good build log: `load build definition from Dockerfile`  
Good runtime log: `[kistie-store] gunicorn on 0.0.0.0:8080`

### Verify

`https://<your-railway-domain>/health/?format=json`
