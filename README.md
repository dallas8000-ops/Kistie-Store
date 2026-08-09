# Kistie-Store

[![CI](https://github.com/dallas8000-ops/Kistie-Store/actions/workflows/ci.yml/badge.svg)](https://github.com/dallas8000-ops/Kistie-Store/actions)

**Live women's fashion ecommerce — curated, imported brands from Turkey, the UK, and the USA, shipping from Kampala to customers worldwide.** Production Django 5.2 storefront + staff tooling + DRF JSON API on Railway / PostgreSQL (SQLite locally), with tests + CI on every push to `main`. Shoppers browse with EU sizing and multi-currency pricing; ordering is supported end-to-end on the site and via WhatsApp.

| | |
|---|---|
| **Live** | https://kistie-store-production.up.railway.app |
| **Code** | https://github.com/dallas8000-ops/Kistie-Store |
| **Trello** | https://trello.com/b/s8Rpm9in/kistie-store |
| **Planning** | `PROJECT_PLANNING.md` |

---

## What it does (short)

**Shoppers:** the storefront is one **Shop** page (`/shop/`). Opening `/` sends visitors straight there. Everything you browse — filters (category, price), EU sizing, currency & payment choices, product quick-view modal, add to cart — lives in that single Shop template (`core/shop.html`). Then cart → checkout, auth, contact. There is no separate "catalog" or "inventory" screen in the UI; former URLs only redirect for old bookmarks (see note below).

Payments are confirmed by staff in the real world; order status is updated in Django admin when admin is enabled (typical for a boutique + East Africa payment mix).

**Operations:** custom-theme Django admin (when enabled), staff dashboard (`/staff/dashboard/`), audit log for superusers, CSRF + login throttling, public-read / staff-only-write JSON API (REST routes live under `/api/inventory/` as a URL prefix only — not a second storefront).

**Why this stack:** Django SSR for the live path (SEO, sessions, security); React + Vite in `frontend/` for experiments/future pages; DRF exposes JSON for integrations.

---

## Recent updates

- **AI shopping assistant** end-to-end (`/api/chat/` + shop chatbot UI); **size assistance** (quick-view `/api/size-recommend/` + chatbot measurement parsing); **fit recommendation** (`/api/fit-recommend/`); contact-inquiry auto-classification; review sentiment on approval; staff demand forecasting; staff AI description generator (`/api/ai/describe/`) for English + Luganda.
- Smart shop search uses optional AI parsing for natural-language queries like color, size, and budget hints.
- **Windows local dev starter** `scripts/start-local.ps1`: starts Django, waits for `/health/`, then Vite — so the SPA never opens before the API is ready.
- Vite proxy covers all `/api` (not only `/api/inventory`) for same-origin dev requests; React uses relative `/api/inventory` unless `VITE_API_BASE_URL` overrides it.
- Dev CORS allows credentialed API calls from `localhost:5173` / `127.0.0.1:5173`; `CSRF_TRUSTED_ORIGINS` includes those origins when `DEBUG=True`.

---

## Pages & features

| Page | URL | What it does |
|---|---|---|
| Entry | `/` | Redirects to `/shop/` |
| Shop | `/shop/` | Only customer-facing browse/buy experience (`core/shop.html`) |
| About | `/about/` | Brand story |
| Cart | `/cart/` | Line items, server-side totals, currency conversion |
| Checkout | `/checkout/` | Order capture, payment instructions, order reference |
| Auth | `/signup/` `/login/` `/logout/` | Shopper accounts; guest cart merges on login |
| Staff sign in | `/staff/login/` | Staff portal entry → staff dashboard |
| Contact | `/contact/` | Inquiry form → DB + SMTP email |
| Terms | `/terms/` | Terms of Service |
| Staff dashboard | `/staff/dashboard/` | Orders snapshot, low-stock alerts, recent inquiries (permission-gated) |
| Staff audit log | `/staff/audit-log/` | Superuser audit trail (permission-gated) |
| Order history | `/account/orders/` | Signed-in shopper orders |
| Admin | `/admin/` | Django admin when `DJANGO_ENABLE_ADMIN` is true; products, images, orders, users |
| Health | `/health/` | Uptime JSON → `{"status":"ok","service":"kistie-store"}` |

**Bookmark compatibility (not extra pages):** old paths `/catalog/` and `/inventory/` redirect to `/shop/` (query string preserved). For demos and reports, treat **Shop** as the only storefront — the redirects exist so legacy bookmarks don't 404.

---

## JSON API & shop helpers

| Area | Path | Notes |
|---|---|---|
| Inventory API | `/api/inventory/…` | DRF: `products/`, `categories/`, `pay/checkout/` (stub). URL prefix only — not a second storefront UI |
| Chat (AI assistant) | `POST /api/chat/` | Shopping assistant used by the Shop page |
| Size recommendation | `POST /api/size-recommend/` | Quick-view / sizing guidance |
| Fit recommendation | `POST /api/fit-recommend/` | Product-specific fit guidance, return risk, and bundle suggestions |
| Staff AI copy | `POST /api/ai/describe/` | Product description helper (English + Luganda); staff-facing |

---

## Tech stack

Python · Django 5.2 · Django REST Framework · PostgreSQL (prod) / SQLite (dev) · Gunicorn · WhiteNoise · Railway · GitHub Actions · Bootstrap 5 · Bootstrap Icons · custom CSS (gradients + branded buttons) · Pillow · requests (HTTP integrations) · optional OpenAI / Google Gemini (AI features via env-configured keys)

---

## Repository layout

Paths below are from the repository root (the same layout CI and Railway use).

- **`requirements.txt`** — Python dependencies. Install with `pip install -r requirements.txt` from the repo root, then run Django commands from `backend/` (`python manage.py …`).
- **`backend/`** — Django project: `manage.py`; `core/` (settings, root `urls.py`, middleware, templates under `core/templates/core/`); `inventory/` (product models + DRF, mounted at `/api/inventory/`); `cart/`; `pages/` (e.g. contact-inquiry model).
- **`frontend/`** — Vite + React. Used for experiments / future SPA work; the production storefront HTML is rendered by Django, not this bundle. Optional: `npm install`, `npm run dev` (Vite dev server, typically port 5173), `npm run demo` (Playwright smoke tests).
- **`payments/`** — Node service for Pesapal redirect handling.
- **`scripts/`** — `capture_screenshots.py`; Windows dev helper `start-local.ps1` (Django first, then Vite).
- **`docs/`** — `demo-presentation.html`, Capstone deliverable scaffold.
- **`.github/workflows/ci.yml`** — installs root `requirements.txt`, then `cd backend && python manage.py test` (Python 3.12).
- **`railway.toml`** — Railway service config (Gunicorn `--chdir backend`, build that runs `collectstatic`, `migrate`, `seed_inventory_if_empty`, and `link_static_images_to_products`).

---

## Run locally

From the repository root (where `requirements.txt` lives):

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt

cd backend
cp .env.example .env   # set DJANGO_SECRET_KEY (and optional vars below)

python manage.py migrate
python manage.py runserver
# http://127.0.0.1:8000/ → redirects to /shop/
# python manage.py createsuperuser → /admin/ when DJANGO_ENABLE_ADMIN allows it
```

**Windows (recommended):** waits for `GET /health/` on `:8000`, then starts Vite and opens both URLs.

```powershell
powershell -ExecutionPolicy Bypass -File "scripts\start-local.ps1"
```

### Fewer flaky loads

- **`DATABASE_URL` in `backend/.env`** — if it points at a cloud DB that's asleep or unreachable, pages can hang. For pure local work, leave `DATABASE_URL` unset so Django uses SQLite (`db.sqlite3`).
- **Frontend before backend** — if you open Vite (`:5173`) before Django is listening on `:8000`, the React app can fail until you refresh. Start Django first (or use the script above).

The React dev app uses relative `/api/inventory` URLs so the browser talks to Vite, which forwards to Django — same-origin in dev, avoiding most CORS/cookie issues. Override with `VITE_API_BASE_URL` only if you need a different API host.

---

## Optional: AI, pricing scan, and related settings

Set these in `backend/.env` (never commit secrets). If keys are missing, AI-assisted endpoints degrade gracefully where implemented.

| Variable | Purpose |
|---|---|
| `AI_PROVIDER` | `openai` or `gemini` (which backend to try first) |
| `OPENAI_API_KEY` | OpenAI API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `OPENAI_MODEL` | Override model (default `gpt-4o-mini`) |
| `GEMINI_MODEL` | Override model (default `gemini-2.0-flash`) |
| `FIT_RECOMMENDER_USE_AI` | `true` or `false`; controls whether fit guidance uses the AI-generated shopper message when a provider key is available |
| `SERPAPI_API_KEY` | Optional web/price tooling |
| `PRICE_SCAN_UGX_RATE` | FX hint for scans (default 3700) |
| `PRICE_SCAN_SITE_BASE_URL` | Optional base URL for price-scan features |

Inventory helpers (run from `backend/`): `load_sample_inventory`, `seed_inventory_if_empty`, `link_static_images_to_products`, `import_web_comparison_prices`, `scan_inventory_prices`, `load_static_images_inventory` — use `--help` per command.

---

## Gmail SMTP (real outbound mail)

Use `backend/.env` locally (copy from `backend/.env.example`). Never commit `.env`.

1. Turn on 2-Step Verification on the Google account.
2. Create an **App password**: Google Account → Security → App passwords → generate one for Mail.
3. Set:
   - `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
   - `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=True`
   - `EMAIL_HOST_USER` / `DJANGO_DEFAULT_FROM_EMAIL` = that Gmail address
   - `EMAIL_HOST_PASSWORD` = the 16-character app password
   - `CONTACT_RECIPIENT_EMAIL` = inbox that should receive contact-form messages

On Railway, add the same variables under the web service's environment (don't paste secrets into the repo). Restart after changing env vars; the Contact page's console-only banner disappears when SMTP is active.

---

## Deploy (Railway)

Railway runs the Django web service from `railway.toml` (Gunicorn `--chdir backend`) with a managed PostgreSQL plugin.

1. Add the **PostgreSQL** plugin → Railway sets `DATABASE_URL` automatically.
2. Set environment variables on the web service:
   - `DJANGO_SECRET_KEY` — long random secret
   - `DJANGO_DEBUG=false`
   - `ALLOWED_HOSTS` — include your Railway hostname (and any custom domain), comma- or space-separated
   - `CSRF_TRUSTED_ORIGINS` — full origins with scheme, e.g. `https://kistie-store-production.up.railway.app`
   - `DJANGO_ENABLE_ADMIN` — `true` only if you want `/admin/` exposed in production
3. The build runs `collectstatic`, `migrate`, `seed_inventory_if_empty`, and `link_static_images_to_products`. Deploy.

### Custom domain

In **Railway → your service → Settings → Networking → Custom Domain**, add the domain and follow the DNS instructions (usually a CNAME). Then extend the two host variables so checkout and forms keep working under `DEBUG=False`:

- `ALLOWED_HOSTS` — add your hostname(s), e.g. `kistie-store-production.up.railway.app,yourbrand.com,www.yourbrand.com`
- `CSRF_TRUSTED_ORIGINS` — add full origins, e.g. `https://yourbrand.com,https://www.yourbrand.com`

### Production hardening

When `DEBUG=False`: HTTPS proxy headers respected (`X-Forwarded-Proto`), secure session + CSRF cookies, SSL redirect, `X-Frame-Options: DENY`, structured logging to stdout (level via `DJANGO_LOG_LEVEL`). Optional HSTS: set `DJANGO_HSTS_SECONDS` (e.g. `31536000`), optionally `DJANGO_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_HSTS_PRELOAD`. Dev CORS for Vite runs only when `DEBUG=True`.

**Health check:** `GET https://kistie-store-production.up.railway.app/health/?format=json` → `{"status":"ok","service":"kistie-store"}` for uptime monitors.

---

## Pesapal payment redirect (production)

Checkout can forward Pesapal orders to a small Node payments service. Locally the app defaults to `http://127.0.0.1:5000/api/pay/pesapal`. In production, set:

```
PESAPAL_INITIATE_URL=https://<your-deployed-payments-host>/api/pay/pesapal
```

See `backend/.env.example`. Restart the web service after changing env vars.

---

## Demo access

- **Live site:** `/` → `/shop/`, `/about/`, `/staff/login/`, etc.
- **Django admin:** `/admin/` — available when `DJANGO_ENABLE_ADMIN=true` (local default on; production default off). Create a superuser locally with `createsuperuser`, or use credentials issued privately for reviewers.
- **Questions:** dallas8000@gmail.com

---

## CI

`.github/workflows/ci.yml` — `pip install -r requirements.txt`, then `cd backend && python manage.py test` on push/PR to `main` or `master` (Python 3.12).

---

## Contact

**Barney R. Gilliom** — built and runs this stack for Kistie-Store as a live retail business.
dallas8000@gmail.com · [GitHub](https://github.com/dallas8000-ops) · [Portfolio](https://gilliomfrontlinedigital.com)
