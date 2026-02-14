#!/usr/bin/env python3
"""Install frontend dependencies (npm install). Run from repo root."""
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
    subprocess.run([npm, "install"], cwd=FRONTEND_DIR)
    sys.exit(0)


if __name__ == "__main__":
    main()
