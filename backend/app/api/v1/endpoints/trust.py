from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from app.core.database import get_session
from app.models.website import Website


router = APIRouter()


@router.get("/stats")
def get_trust_stats(session: Session = Depends(get_session)) -> dict[str, int]:
    """Get public trust statistics."""
    # Count total websites being monitored
    total_websites = session.exec(select(func.count(Website.id))).one()
    
    # Count active websites (websites that have been scanned recently)
    # For now, we'll just return total websites
    active_websites = total_websites  # Can be refined later
    
    return {
        "total_websites": total_websites,
        "active_websites": active_websites,
    }
