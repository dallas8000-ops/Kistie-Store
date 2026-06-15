#!/usr/bin/env python
"""Root wrapper so Railpack detects Django (real project lives in ``backend/``)."""
import os
import sys

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")


def main() -> None:
    os.chdir(BACKEND)
    sys.path.insert(0, BACKEND)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    argv = [os.path.join(BACKEND, "manage.py"), *sys.argv[1:]]
    os.execv(sys.executable, [sys.executable, *argv])


if __name__ == "__main__":
    main()
