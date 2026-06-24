from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.behavior_store import compute_behavior_score, record_behavior_events
from app.models.user import User


router = APIRouter()


class BehaviorEvent(BaseModel):
    type: str = Field(min_length=2, max_length=60)
    path: str | None = None
    timestamp: str | None = None
    meta: dict[str, str] = Field(default_factory=dict)


class BehaviorEventBatch(BaseModel):
    events: list[BehaviorEvent]


@router.post("/events")
def ingest_behavior_events(
    payload: BehaviorEventBatch,
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    events = [
        {
            "type": item.type,
            "path": item.path,
            "timestamp": item.timestamp or datetime.now(timezone.utc).isoformat(),
            "meta": item.meta,
        }
        for item in payload.events
    ]
    record_behavior_events(str(current_user.tenant_id), str(current_user.id), events)
    return {"stored_events": len(events)}


@router.get("/score")
def get_behavior_score(current_user: User = Depends(get_current_user)) -> dict[str, object]:
    return compute_behavior_score(str(current_user.tenant_id), str(current_user.id))