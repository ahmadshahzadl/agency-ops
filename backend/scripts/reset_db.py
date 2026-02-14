"""Reset database: drop all tables, run all migrations, seed all data.

Does the following in order:
  1. Drop all tables ............ alembic downgrade base
  2. Run all migrations ......... alembic upgrade head
  3. Seed permissions & roles ... scripts/seed_db.py (admin, manager, member, viewer)
  4. Seed demo data .............. scripts/seed_demo_data.py (teams, leads, clients, projects, tasks, etc.)

Run from backend directory (or use the root-level script):
  cd backend
  python scripts/reset_db.py

Options:
  --no-seed   Skip seeding; only drop tables and run migrations.
"""
import os
import sys
import subprocess

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)


def run(cmd: list[str]) -> bool:
    r = subprocess.run(cmd, cwd=BACKEND_DIR)
    return r.returncode == 0


def main():
    no_seed = "--no-seed" in sys.argv
    print("=== Database reset ===\n")
    print("1. Dropping all tables (alembic downgrade base)...")
    if not run([sys.executable, "-m", "alembic", "downgrade", "base"]):
        print("   FAILED: alembic downgrade base")
        sys.exit(1)
    print("   Done.\n")
    print("2. Running all migrations (alembic upgrade head)...")
    if not run([sys.executable, "-m", "alembic", "upgrade", "head"]):
        print("   FAILED: alembic upgrade head")
        sys.exit(1)
    print("   Done.\n")
    if no_seed:
        print("Seeding skipped (--no-seed). Run seed_db.py and seed_demo_data.py manually if needed.")
        return
    print("3. Seeding permissions, roles & admin user (seed_db.py)...")
    if not run([sys.executable, os.path.join("scripts", "seed_db.py")]):
        print("   FAILED: seed_db.py")
        sys.exit(1)
    print("   Done.\n")
    print("4. Seeding demo data (seed_demo_data.py)...")
    if not run([sys.executable, os.path.join("scripts", "seed_demo_data.py")]):
        print("   FAILED: seed_demo_data.py")
        sys.exit(1)
    print("   Done.\n")
    print("=== Database reset complete ===")
    print("  Admin:  admin@example.com / admin123")
    print("  Others: manager@example.com, member@example.com, viewer@example.com / demo123")


if __name__ == "__main__":
    main()
