from fastapi import APIRouter
from app.api import auth, ingest, logs, admin, analytics

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(logs.router, prefix="/teams", tags=["logs"])
api_router.include_router(analytics.router, prefix="/teams", tags=["analytics"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
