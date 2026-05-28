HOW TO RUN KISTIE STORE LOCALLY (WINDOWS-FRIENDLY)
==================================================

WHAT YOU NEED
-------------
  - Python 3.12 recommended (matches CI)
  - pip
  - Node.js 18+ and npm — only if you want the experimental React frontend (frontend folder)

SETUP (DJANGO STORE — MAIN APP)
-------------------------------
Open a terminal in the PROJECT ROOT folder (the one containing "backend" and "frontend").

1) Install Python dependencies (run from PROJECT ROOT):

   python -m pip install --upgrade pip
   pip install -r requirements.txt

2) Configure environment:

   cd backend
   copy .env.example .env

   Edit .env and set DJANGO_SECRET_KEY to any random string for local use.
   For local SQLite (simplest): do NOT set DATABASE_URL. If DATABASE_URL points
   to a cloud database that is off-line, the app may fail or hang.

3) Apply database migrations:

   python manage.py migrate

4) Start the server:

   python manage.py runserver 127.0.0.1:8000

5) Open a browser:

   http://127.0.0.1:8000/

   "/" redirects to the shop at "/shop/". Health check JSON:

   http://127.0.0.1:8000/health/?format=json

Optional: create an admin login (staff features):

   python manage.py createsuperuser

ADMIN is available only when ENABLE_ADMIN/DJANGO_ENABLE_ADMIN allows it locally.

OPTIONAL — REACT + VITE (frontend experiments)
----------------------------------------------
The live customer storefront is Django. The frontend folder is a separate dev shell.

Open a SECOND terminal:

   cd frontend
   npm install
   npm run dev

Browser: http://127.0.0.1:5173/

Vite proxies /api to Django on port 8000. Start Django first, or reload the SPA
once the backend is ready.

OPTIONAL — START BOTH AT ONCE (WINDOWS)
---------------------------------------
From PROJECT ROOT:

   powershell -ExecutionPolicy Bypass -File scripts\start-local.ps1

This waits for Django /health/, then starts Vite and opens both URLs.

TROUBLESHOOTING (QUICK)
-----------------------
  - Blank or failed SPA loads on :5173: ensure Django is already running on :8000.
  - Strange DB errors locally: comment out DATABASE_URL in backend\.env so SQLite is used.
  - Missing Bootstrap look: templates use a CDN — you need internet for first paint.
  - Never commit secrets: keep real keys only in backend\.env (gitignored).

MORE DETAIL
-----------
See README.md in this folder for full documentation.
