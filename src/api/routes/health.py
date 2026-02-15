from typing import Any

from fastapi import APIRouter

from src.config.settings import get_settings
from src.storage.postgres import get_postgres_connection

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check including database connectivity."""

    settings = get_settings()
    postgres = get_postgres_connection()

    db_healthy = await postgres.health_check()

    return {
        "status": "ready" if db_healthy else "not_ready",
        "checks": {
            "database": "healthy" if db_healthy else "unhealthy",
            "langfuse": "enabled" if settings.is_langfuse_configured else "disabled",
        },
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive"}
