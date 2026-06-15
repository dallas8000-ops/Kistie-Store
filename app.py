"""Railway Railpack entrypoint when Dockerfile builder is not used.

Django lives in ``backend/``. Railpack runs ``python app.py || python main.py`` when
``manage.py`` is not at the repo root.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = os.environ.get("PORT", "8080")
PYTHON = sys.executable


def _run(cmd: list[str], *, optional: bool = False) -> None:
    print(f"[kistie-store] running: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0 and not optional:
        print(f"[kistie-store] command failed with exit code {result.returncode}", flush=True)
        sys.exit(result.returncode)


def main() -> None:
    print(f"[kistie-store] booting on 0.0.0.0:{PORT} (python={PYTHON})", flush=True)
    _run([PYTHON, "backend/manage.py", "migrate", "--noinput"])
    _run([PYTHON, "backend/manage.py", "seed_inventory_if_empty"], optional=True)
    _run([PYTHON, "backend/manage.py", "link_static_images_to_products"], optional=True)
    gunicorn_cmd = [
        PYTHON,
        "-m",
        "gunicorn",
        "core.wsgi:application",
        "--chdir",
        "backend",
        "--bind",
        f"0.0.0.0:{PORT}",
        "--workers",
        "2",
        "--timeout",
        "120",
    ]
    print(f"[kistie-store] starting gunicorn on 0.0.0.0:{PORT}", flush=True)
    os.execv(PYTHON, gunicorn_cmd)


if __name__ == "__main__":
    main()
