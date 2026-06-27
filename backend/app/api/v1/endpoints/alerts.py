from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.cache import cache_get, cache_set, cache_delete_pattern
from app.core.database import get_session
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertRead


router = APIRouter()
ALERTS_CACHE_PREFIX = "alerts"

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class AlertsPage(BaseModel):
    items: list[AlertRead]
    next_cursor: Optional[str] = None


@router.get("", response_model=AlertsPage)
def list_alerts(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, alias="status"),
    channel: Optional[str] = Query(None),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    cursor: Optional[str] = Query(None),
) -> AlertsPage:
    """List alerts with keyset pagination."""
    tenant_id = str(current_user.tenant_id)

    cache_key = (
        f"{ALERTS_CACHE_PREFIX}:{tenant_id}:{status_filter or ''}:"
        f"{channel or ''}:{limit}:{cursor or ''}"
    )
    cached = cache_get(cache_key)
    if cached is not None:
        return AlertsPage(**cached)

    query = select(Alert).where(Alert.tenant_id == current_user.tenant_id)

    if status_filter:
        query = query.where(Alert.status == status_filter)
    if channel:
        query = query.where(Alert.channel == channel)
    if cursor:
        cursor_ts, _, cursor_id = cursor.partition("|")
        try:
            cursor_dt = datetime.fromisoformat(cursor_ts)
            cursor_uuid = UUID(cursor_id)
            query = query.where(
                (Alert.created_at < cursor_dt)
                | ((Alert.created_at == cursor_dt) & (Alert.id < cursor_uuid))
            )
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid cursor")

    query = query.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit + 1)

    rows = session.exec(query).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [AlertRead.model_validate(row) for row in rows]
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = f"{last.created_at.isoformat()}|{last.id}"

    response = AlertsPage(items=items, next_cursor=next_cursor)
    cache_set(cache_key, response.model_dump(mode="json"), ttl=30)
    return response


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    alert = session.exec(select(Alert).where(Alert.id == alert_id, Alert.tenant_id == current_user.tenant_id)).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    session.delete(alert)
    session.commit()
    cache_delete_pattern(f"{ALERTS_CACHE_PREFIX}:{current_user.tenant_id}")
    return {"status": "deleted"}