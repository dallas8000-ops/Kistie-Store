# Kistie-Store

[![CI](https://github.com/dallas8000-ops/Kistie-Store/actions/workflows/ci.yml/badge.svg)](https://github.com/dallas8000-ops/Kistie-Store/actions/workflows/ci.yml)

Live **fashion ecommerce** (women’s apparel & accessories)—shipping from **Kampala**, serving customers online worldwide. Production **Django** storefront + staff tooling + **DRF** API on **Render** / **PostgreSQL**, **tests + CI** on every push to `main`.

| | |
|--|--|
| **Live** | **[Kistie-Store](https://kristie-store.onrender.com)** on Render — `https://kristie-store.onrender.com` |
| **Code** | https://github.com/dallas8000-ops/Kistie-Store |
| **Trello** | https://trello.com/b/s8Rpm9in/kistie-store |
| **Planning** | [PROJECT_PLANNING.md](PROJECT_PLANNING.md) |

> **Note:** The Render subdomain uses the spelling **`kristie-store`**; the product/repo branding is **Kistie**. Links and `ALLOWED_HOSTS` must match the hostname Render assigns.

---

## Latest update (May 19, 2026)

- README refresh: documented **optional AI / pricing env vars**, **shop JSON endpoints** (`/api/chat/`, `/api/size-recommend/`, `/api/ai/describe/`), **production Django admin toggle** (`DJANGO_ENABLE_ADMIN`), **Render build pipeline** (migrate + seed + image linking), and corrected **local setup** (`pip install -r requirements.txt` from repo root before `cd backend`).
- Earlier (May 18, 2026): AI shopping assistant end-to-end (`/api/chat/` + shop chatbot UI); size assistance (quick-view `/api/size-recommend/` + chatbot measurement parsing); contact inquiry auto-classification; review sentiment on approval; staff demand forecasting; staff AI description generator (`/api/ai/describe/`) for English + Luganda; chatbot UX/resilience improvements.

---

## What it does (short)

**Shoppers:** the storefront is **one Shop page** (`/shop/`). Opening **`/`** sends visitors straight there. Everything you browse—filters (category, price), EU sizing, currency & payment choices, product quick-view modal, add to cart—lives in that single Shop template (`core/shop.html`). Then cart → checkout, auth, contact. **There is no separate “catalog” or “inventory” screen** in the UI; former URLs only redirect for old bookmarks (see note below).

**Payments** are confirmed by staff in the real world; order status is updated in **Django admin** when admin is enabled (typical for boutique + East Africa payment mix).

**Operations:** custom-theme **Django admin** (when enabled), **staff dashboard** (`/staff/dashboard/`), **audit log** for superusers, CSRF + login throttling, **public read / staff-only write** on the JSON API (REST routes live under **`/api/inventory/`** as a URL prefix only—not a second storefront).

**Why this stack:** Django **SSR** for the live path (SEO, sessions, security); **React + Vite** in `frontend/` for experiments/future pages; DRF exposes JSON for integrations.

---

## Repository layout

Paths below are from the **repository root** (same layout CI and Render use).

- **`requirements.txt`** — Python dependencies. Install with `pip install -r requirements.txt` from the repo root, then run Django commands from **`backend/`** (`python manage.py …`).
- **`backend/`** — Django project: `manage.py`; **`core/`** (settings, root `urls.py`, middleware, templates under `core/templates/core/`); **`inventory/`** (product models + DRF, mounted at `/api/inventory/`); **`cart/`**; **`pages/`** (e.g. contact inquiry model).
- **`frontend/`** — Vite + React (`package.json`, app code under `frontend/src/`). Used for experiments / future SPA work; **production storefront HTML is rendered by Django**, not this bundle. Optional: `npm install`, `npm run dev` (Vite dev server, typically port **5173**), `npm run demo` (Playwright smoke tests in `frontend/tests/`).
- **`payments/`** — Node service for Pesapal redirect handling (`package.json`).
- **`scripts/`** — Automation such as [`scripts/capture_screenshots.py`](scripts/capture_screenshots.py).
- **`docs/`** — Static materials such as [`docs/demo-presentation.html`](docs/demo-presentation.html).
- **`images/`** — Source imagery; **`images/screenshots/`** — README screenshot gallery (see **Proof — screenshots** below).
- **[`.github/workflows/ci.yml`](.github/workflows/ci.yml)** — installs root `requirements.txt`, then `cd backend && python manage.py test` (Python **3.12**).
- **[`render.yaml`](render.yaml)** — Render web service (`gunicorn --chdir backend`), Postgres, and a build command that runs **collectstatic**, **migrate**, **`seed_inventory_if_empty`**, and **`link_static_images_to_products`**.

---

## Pages & features

| Page | URL | What it does |
|------|-----|--------------|
| Entry | `/` | **Redirects to** `/shop/` |
| Shop | `/shop/` | Only customer-facing browse/buy experience (`backend/core/templates/core/shop.html`; Django name `core/shop.html`) |
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
| Admin | `/admin/` | Django admin **only when** `DJANGO_ENABLE_ADMIN` is true (disabled by default on Render per [`render.yaml`](render.yaml)); products, images, orders, users |
| Health | `/health/` | Uptime JSON → `{"status":"ok","service":"kistie-store"}` |

### JSON API & shop helpers

| Area | Path | Notes |
|------|------|--------|
| Inventory API | `/api/inventory/` … | DRF: `products/`, `categories/`, `pay/checkout/` (stub). **URL prefix only** — not a second storefront UI |
| Chat (AI assistant) | `POST /api/chat/` | Shopping assistant used by the Shop page |
| Size recommendation | `POST /api/size-recommend/` | Quick-view / sizing guidance |
| Staff AI copy | `POST /api/ai/describe/` | Product description helper (English + Luganda); staff-facing usage |

**Bookmark compatibility (not extra pages):** old paths **`/catalog/`** and **`/inventory/`** **redirect** to **`/shop/`** (query string preserved). For demos and reports, treat **Shop** as the only storefront—the redirects exist so legacy bookmarks do not 404.

---

## Tech (recruiter lines)

Python · **Django 5.2** · **Django REST Framework** · **PostgreSQL** (prod) / SQLite (dev) · Gunicorn · WhiteNoise · **Render** · **GitHub Actions** · Bootstrap 5 · **Bootstrap Icons** · custom CSS (gradients + branded buttons) · Pillow · **requests** (HTTP integrations) · optional **OpenAI** / **Google Gemini** (AI features via env-configured keys)

---

## Proof — screenshots

**Gallery:** [`images/screenshots/`](images/screenshots/) — regenerate via [`scripts/capture_screenshots.py`](scripts/capture_screenshots.py) (Playwright). Start Django (`runserver`), then from repo root:

```bash
python scripts/capture_screenshots.py
```

Uses **`http://127.0.0.1:8000`** by default; override with **`SCREENSHOT_BASE_URL`** if needed.

**Samples:**

| Shop (`/shop/`) | About |
|-----------------|-------|
| ![Shop](images/screenshots/shop.png) | ![About](images/screenshots/about.png) |

| Contact | Terms |
|---------|-------|
| ![Contact](images/screenshots/contact.png) | ![Terms](images/screenshots/terms.png) |

| Django admin login | Staff sign-in |
|--------------------|---------------|
| ![Admin login](images/screenshots/admin-login.png) | ![Staff login](images/screenshots/staff-login.png) |

Also in folder: `cart.png`, `login.png`, `signup.png`. Signed-in **admin product grids** depend on your data — capture manually after login if needed.

**Slide deck:** [`docs/demo-presentation.html`](docs/demo-presentation.html) (serve locally with `python -m http.server 8080` from repo root).

---

## Demo access

- **Live site:** **`/`** → **`/shop/`**, `/about/`, `/staff/login/`, etc.
- **Django admin:** `/admin/` — available when **`DJANGO_ENABLE_ADMIN=true`** (local default is on; production [`render.yaml`](render.yaml) defaults it **off**). Create a superuser locally with `createsuperuser`, or use credentials issued privately for reviewers.
- **Questions:** [dallas8000@gmail.com](mailto:dallas8000@gmail.com).

---

## Run locally

From the **repository root** (where `requirements.txt` lives):

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt

cd backend
cp .env.example .env   # set DJANGO_SECRET_KEY (and optional vars below)

python manage.py migrate
python manage.py runserver
# http://127.0.0.1:8000/ → redirects to /shop/
# python manage.py createsuperuser  → /admin/ when ENABLE_ADMIN is on
```

Optional: **`frontend/`** (`npm install`, `npm run dev`) and **`payments/`** for React/Node experiments. See [`render.yaml`](render.yaml) for production service shape.

---

## Optional: AI, pricing scan, and related settings

Set these in **`backend/.env`** (never commit secrets). If keys are missing, AI-assisted endpoints degrade gracefully where implemented.

| Variable | Purpose |
|----------|---------|
| `AI_PROVIDER` | `openai` or `gemini` (which backend to try first; see `settings.py`) |
| `OPENAI_API_KEY` | OpenAI API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `OPENAI_MODEL` | Override model (default `gpt-4o-mini`) |
| `GEMINI_MODEL` | Override model (default `gemini-2.0-flash`) |
| `SERPAPI_API_KEY` | Optional web/price tooling (see inventory management commands) |
| `PRICE_SCAN_UGX_RATE` | FX hint for scans (default `3700`) |
| `PRICE_SCAN_SITE_BASE_URL` | Optional base URL for price-scan features |

Inventory helpers (run from `backend/`): e.g. `load_sample_inventory`, `seed_inventory_if_empty`, `link_static_images_to_products`, `import_web_comparison_prices`, `scan_inventory_prices`, `load_static_images_inventory` — use `--help` per command for options.

---

## Gmail SMTP (real outbound mail)

Use **`backend/.env`** locally (copy from [`backend/.env.example`](backend/.env.example)). Never commit `.env`.

1. Turn on **2-Step Verification** on the Google account.
2. Create an **App password**: Google Account → **Security** → **App passwords** → generate one for Mail.
3. Set:
   - `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
   - `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=True`
   - `EMAIL_HOST_USER` / `DJANGO_DEFAULT_FROM_EMAIL` = that Gmail address
   - `EMAIL_HOST_PASSWORD` = the **16-character app password** (not your normal Gmail password)
   - `CONTACT_RECIPIENT_EMAIL` = inbox that should receive contact form messages

On **Render**, add the same variables under **Environment** for the web service (do not paste secrets into the repo).

Restart the app after changing env vars. The Contact page **console-only banner** disappears when SMTP is active.

---

## Production hardening

When **`DEBUG=False`** (Render): **HTTPS proxy headers** respected (`X-Forwarded-Proto`), **secure session + CSRF cookies**, **SSL redirect**, **`X-Frame-Options: DENY`**, structured **logging** to stdout (level via `DJANGO_LOG_LEVEL`). Optional **HSTS**: set `DJANGO_HSTS_SECONDS` (e.g. `31536000`), optionally `DJANGO_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_HSTS_PRELOAD`. **Dev CORS** for Vite runs **only when `DEBUG=True`**.

**Health checks:** `GET https://kristie-store.onrender.com/health/?format=json` → `{"status":"ok","service":"kistie-store"}` for uptime monitors.

---

## Custom domain on Render

Render gives **HTTPS** on your `*.onrender.com` URL automatically. To use **your own domain** (e.g. `www.yourbrand.com`):

1. In Render → your **Web Service** → **Settings** → **Custom Domains** → add the domain and follow **DNS** instructions (usually CNAME to `your-service.onrender.com`).
2. Set environment variables on the web service so Django accepts the host and CSRF POSTs:
   - **`ALLOWED_HOSTS`** — include your hostname (comma or space separated), e.g. `kristie-store.onrender.com,yourbrand.com,www.yourbrand.com`
   - **`CSRF_TRUSTED_ORIGINS`** — include full origins with scheme, e.g. `https://kristie-store.onrender.com,https://yourbrand.com,https://www.yourbrand.com`

Render already injects **`RENDER_EXTERNAL_HOSTNAME`** for the default service URL; custom domains need the two variables above (or extend them) so checkout and forms keep working under **`DEBUG=False`**.

---

## Pesapal payment redirect (production)

Checkout can forward **Pesapal** orders to a small **Node payments** service. Locally the app defaults to `http://127.0.0.1:5000/api/pay/pesapal`. On Render, set:

`PESAPAL_INITIATE_URL=https://<your-deployed-payments-host>/api/pay/pesapal`

See [`backend/.env.example`](backend/.env.example). Restart the web service after changing env vars.

---

## Promoting the live site (organic)

- **Public HTTPS URL:** use **`https://kristie-store.onrender.com`** (or your custom domain) everywhere—Instagram bio, Linktree-style link pages, WhatsApp status, email signature.
- **Link-in-bio tools** (e.g. Linktree): add **one button** → paste the same store URL; you do not rebuild the shop there.
- **Paid ads:** optional; even a low daily cap works better with **one clear landing URL** and consistent messaging.

---

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) — `pip install -r requirements.txt` then `cd backend && python manage.py test` on **push/PR** to `main` or `master` (Python **3.12**).

---

## Contact

**Barney R. Gilliom** — built and runs this stack for **Kistie-Store** as a live retail business.

dallas8000@gmail.com · [LinkedIn](https://www.linkedin.com/in/barney-gilliom-959981337) · [GitHub](https://github.com/dallas8000-ops) · [Portfolio](https://jnalumansi.onrender.com)

Business questions: use the **live site** contact or the email above.
