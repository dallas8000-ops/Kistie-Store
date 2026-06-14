"""Railway Railpack entrypoint when Dockerfile builder is not used.

Django lives in ``backend/``; Railpack looks for ``app.py`` / ``main.py`` at the
repo root. Delegate to the shared start script so gunicorn binds ``$PORT``.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
START_SCRIPT = os.path.join(ROOT, "scripts", "railway-start.sh")

if __name__ == "__main__":
    sys.exit(subprocess.call(["sh", START_SCRIPT], cwd=ROOT))
