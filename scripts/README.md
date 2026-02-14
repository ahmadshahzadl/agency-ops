# Scripts

Run all scripts from **repo root** unless noted.

## Database

### Reset database (drop tables → migrations → seed)
```bash
python scripts/reset_database.py
python scripts/reset_database.py --no-seed   # skip seeding
```
From backend: `cd backend && python scripts/reset_db.py`

## Backend (Python / FastAPI)

| Script | Description |
|--------|-------------|
| `python scripts/run_backend.py` | Start API server (uvicorn, port 8000) |
| `python scripts/install_backend.py` | Install deps (`pip install -r backend/requirements.txt`) |
| `python scripts/test_backend.py` | Run pytest in backend |

## Frontend (React / Vite)

| Script | Description |
|--------|-------------|
| `python scripts/run_frontend.py` | Start dev server (Vite, port 5173) |
| `python scripts/install_frontend.py` | Install deps (`npm install` in frontend) |
| `python scripts/test_frontend.py` | Run frontend build (validates TS and build) |

## Reset steps (reference)

1. `alembic downgrade base` — drop all tables  
2. `alembic upgrade head` — run all migrations  
3. `seed_db.py` — permissions, roles, admin user  
4. `seed_demo_data.py` — teams, leads, clients, projects, etc.

**Demo logins:** admin@example.com / admin123; manager@example.com, member@example.com, viewer@example.com / demo123
