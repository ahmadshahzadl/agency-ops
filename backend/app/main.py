from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.v1 import auth, clients, projects, tasks, meetings, finance, analytics, users, roles, teams, leads, team_activity, announcements, notifications

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(finance.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(roles.router, prefix="/api/v1")
app.include_router(teams.router, prefix="/api/v1")
app.include_router(leads.router, prefix="/api/v1")
app.include_router(team_activity.router, prefix="/api/v1")
app.include_router(announcements.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
