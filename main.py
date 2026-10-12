import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import engine, Base
from app.seed import seed_database

# Routers
from app.routers import (
    auth,
    projects,
    issues,
    collaboration,
    sprints,
    releases,
    webhooks,
    analytics,
    export,
    system,
)

START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise-grade Software Issue Tracking & Resolution Platform with RBAC, Smart Triage, Agile Sprints, and CI/CD Webhooks.",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Routers
api_v1 = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=api_v1)
app.include_router(projects.router, prefix=api_v1)
app.include_router(issues.router, prefix=api_v1)
app.include_router(collaboration.router, prefix=api_v1)
app.include_router(sprints.router, prefix=api_v1)
app.include_router(releases.router, prefix=api_v1)
app.include_router(webhooks.router, prefix=api_v1)
app.include_router(analytics.router, prefix=api_v1)
app.include_router(export.router, prefix=api_v1)
app.include_router(system.router, prefix=api_v1)

# Static & Upload Files
STATIC_DIR = Path(__file__).resolve().parent / "app" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/health", tags=["System"])
def health_check():
    db_type = "postgresql" if "postgres" in settings.DATABASE_URL.lower() else "sqlite"
    uptime = round(time.time() - START_TIME, 2)
    return {
        "status": "healthy",
        "database": db_type,
        "pool_size": settings.DB_POOL_SIZE,
        "uptime_seconds": uptime,
        "version": settings.VERSION,
        "service": "BugFlow Issue Resolution Platform"
    }

@app.get("/", include_in_schema=False)
def serve_frontend():
    index_file = STATIC_DIR / "index.html"
    return FileResponse(str(index_file))