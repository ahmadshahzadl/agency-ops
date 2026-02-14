#!/usr/bin/env python3
"""Start the backend API server (uvicorn). Run from repo root."""
import os
import sys
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")


def find_python():
    if sys.platform == "win32":
        venv_python = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")
    else:
        venv_python = os.path.join(BACKEND_DIR, ".venv", "bin", "python")
    if os.path.isfile(venv_python):
        return venv_python
    return sys.executable


def main():
    if not os.path.isdir(BACKEND_DIR):
        print("Backend directory not found:", BACKEND_DIR)
        sys.exit(1)
    python = find_python()
    # uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    subprocess.run(
        [python, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
        cwd=BACKEND_DIR,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
