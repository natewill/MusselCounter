"""
System-related API endpoints (health, db version, etc.).

These endpoints provide system information and health checks.
They're typically used by the frontend to:
- Check if backend is running
- Detect database resets (to refresh cached data)
"""
from fastapi import APIRouter
from db import get_db, get_db_version
from typing import Dict

router = APIRouter(tags=["system"])
# Note: System endpoints are excluded from rate limiting in main.py


@router.get("/")
def root() -> Dict[str, str]:
    """
    Root endpoint - health check.
    
    Simple endpoint to verify the backend is running and responding.
    """
    return {"message": "Backend running!"}


@router.get("/api/db-version")
async def get_db_version_endpoint() -> Dict[str, str | None]:
    """
    Get the database version/timestamp to detect database resets.
    
    Returns the database initialization timestamp. The frontend can check this
    to detect when the database has been reset (timestamp changes), which
    means all data has been cleared and cached data should be refreshed.
    """
    async with get_db() as db:
        version = await get_db_version(db)
        return {"db_version": version}

