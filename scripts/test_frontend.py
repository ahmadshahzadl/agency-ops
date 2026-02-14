#!/usr/bin/env python3
"""Run frontend build (validates TypeScript and Vite build). Run from repo root."""
import os
import sys
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")


def main():
    if not os.path.isdir(FRONTEND_DIR):
        print("Frontend directory not found:", FRONTEND_DIR)
        sys.exit(1)
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    r = subprocess.run([npm, "run", "build"], cwd=FRONTEND_DIR)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
