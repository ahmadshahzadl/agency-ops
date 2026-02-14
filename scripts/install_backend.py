#!/usr/bin/env python3
"""Install backend dependencies (pip install -r requirements.txt). Run from repo root."""
import os
import sys
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")


def find_pip():
    if sys.platform == "win32":
        venv_pip = os.path.join(BACKEND_DIR, ".venv", "Scripts", "pip.exe")
    else:
        venv_pip = os.path.join(BACKEND_DIR, ".venv", "bin", "pip")
    if os.path.isfile(venv_pip):
        return [venv_pip, "install", "-r", "requirements.txt"]
    return [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]


def main():
    if not os.path.isdir(BACKEND_DIR):
        print("Backend directory not found:", BACKEND_DIR)
        sys.exit(1)
    req = os.path.join(BACKEND_DIR, "requirements.txt")
    if not os.path.isfile(req):
        print("requirements.txt not found in backend")
        sys.exit(1)
    cmd = find_pip()
    subprocess.run(cmd, cwd=BACKEND_DIR)
    sys.exit(0)


if __name__ == "__main__":
    main()
