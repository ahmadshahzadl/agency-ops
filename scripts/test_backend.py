#!/usr/bin/env python3
"""Run backend tests (pytest). Run from repo root."""
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
    r = subprocess.run([python, "-m", "pytest", "tests/", "-v"], cwd=BACKEND_DIR)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
