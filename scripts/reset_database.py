#!/usr/bin/env python3
"""Run full database reset from repo root: drop all tables, run migrations, seed all data.

Usage (from repo root):
  python scripts/reset_database.py
  python scripts/reset_database.py --no-seed

This runs backend/scripts/reset_db.py with the backend virtualenv Python so
alembic and all dependencies are available.
"""
import os
import sys
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")


def find_python():
    """Use backend venv Python if present, else current interpreter."""
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
    script = os.path.join(BACKEND_DIR, "scripts", "reset_db.py")
    if not os.path.isfile(script):
        print("Reset script not found:", script)
        sys.exit(1)
    args = [python, script] + sys.argv[1:]
    r = subprocess.run(args, cwd=BACKEND_DIR)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
