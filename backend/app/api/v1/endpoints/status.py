from datetime import datetime, timezone
from fastapi import APIRouter


router = APIRouter()


@router.get("/public")
def get_public_status() -> dict:
    """Get public system status."""
    # In production, this would check actual service health
    # For now, we return a simple status
    return {
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "api": {"status": "operational", "uptime": "99.9%"},
            "database": {"status": "operational", "uptime": "99.9%"},
            "redis": {"status": "operational", "uptime": "99.9%"},
            "worker": {"status": "operational", "uptime": "99.9%"},
        },
        "incidents": [],  # List of active incidents
    }
