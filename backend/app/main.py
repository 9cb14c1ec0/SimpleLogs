from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.db import init_db, close_db
from app.api import api_router
from app.models import User
from app.services.retention import RetentionService
from app.services.partitions import ensure_upcoming_partitions
from app.migrations import run_migrations

settings = get_settings()
scheduler = AsyncIOScheduler()


async def create_admin_user():
    """Create default admin user if none exists."""
    admin = await User.filter(is_admin=True).first()
    if admin is None:
        admin = User(
            email=settings.admin_email,
            name=settings.admin_name,
            is_admin=True,
        )
        admin.set_password(settings.admin_password)
        await admin.save()
        print(f"Created admin user: {settings.admin_email}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await run_migrations()
    await create_admin_user()
    await ensure_upcoming_partitions()

    # Start retention cleanup scheduler (runs every hour)
    scheduler.add_job(
        RetentionService.cleanup_expired_logs,
        trigger=IntervalTrigger(hours=1),
        id="retention_cleanup",
        replace_existing=True,
    )
    # Ensure next month's partitions exist (runs daily)
    scheduler.add_job(
        ensure_upcoming_partitions,
        trigger=IntervalTrigger(hours=24),
        id="partition_maintenance",
        replace_existing=True,
    )
    scheduler.start()

    yield

    # Shutdown
    scheduler.shutdown()
    await close_db()


app = FastAPI(
    title="SimpleLogs",
    description="A logging storage and search application",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
