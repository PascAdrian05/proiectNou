import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, delete, select

from app.api.deps import get_current_user
from app.core.cache import cache_get, cache_set, cache_delete_pattern
from app.core.database import get_session
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.user import User
from app.schemas.finding import FindingRead


router = APIRouter()
FINDINGS_CACHE_PREFIX = "findings"

# Hard cap so a runaway client can't pull the entire table into memory.
# The UI typically shows the most recent 50.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class FindingsPage(BaseModel):
    """A single page of findings, ordered by ``first_seen_at`` desc."""

    items: list[FindingRead]
    next_cursor: Optional[str] = None


@router.get("", response_model=FindingsPage)
def list_findings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
    website_id: Optional[UUID] = Query(None),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    cursor: Optional[str] = Query(None),
) -> FindingsPage:
    """List findings with keyset pagination.

    ``cursor`` is the ISO timestamp + id of the last row from the previous
    page. Returning timestamps instead of opaque blobs means the API stays
    trivially debuggable with curl.
    """
    tenant_id = str(current_user.tenant_id)

    cache_key = (
        f"{FINDINGS_CACHE_PREFIX}:{tenant_id}:{status_filter or ''}:"
        f"{severity or ''}:{website_id or ''}:{limit}:{cursor or ''}"
    )
    cached = cache_get(cache_key)
    if cached is not None:
        return FindingsPage(**cached)

    query = select(Finding).where(Finding.tenant_id == current_user.tenant_id)

    if status_filter:
        query = query.where(Finding.status == status_filter)
    if severity:
        query = query.where(Finding.severity == severity)
    if website_id:
        query = query.where(Finding.website_id == website_id)
    if cursor:
        cursor_ts, _, cursor_id = cursor.partition("|")
        try:
            cursor_dt = datetime.fromisoformat(cursor_ts)
            cursor_uuid = UUID(cursor_id)
            # Strict less-than so we never re-emit the boundary row.
            query = query.where(
                (Finding.first_seen_at < cursor_dt)
                | ((Finding.first_seen_at == cursor_dt) & (Finding.id < cursor_uuid))
            )
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid cursor")

    # Order by recency, then by id for stable tiebreaking.
    query = query.order_by(Finding.first_seen_at.desc(), Finding.id.desc()).limit(limit + 1)

    rows = session.exec(query).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [FindingRead.model_validate(row) for row in rows]
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = f"{last.first_seen_at.isoformat()}|{last.id}"

    response = FindingsPage(items=items, next_cursor=next_cursor)
    cache_set(cache_key, response.model_dump(mode="json"), ttl=30)
    return response


@router.delete("/{finding_id}")
def delete_finding(
    finding_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    finding = session.exec(select(Finding).where(Finding.id == finding_id, Finding.tenant_id == current_user.tenant_id)).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    session.exec(delete(Alert).where(Alert.finding_id == finding.id))
    session.delete(finding)
    session.commit()
    cache_delete_pattern(f"{FINDINGS_CACHE_PREFIX}:{current_user.tenant_id}")
    return {"status": "deleted"}


@router.post("/{finding_id}/resolve")
def resolve_finding(
    finding_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    finding = session.exec(select(Finding).where(Finding.id == finding_id, Finding.tenant_id == current_user.tenant_id)).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    finding.status = "resolved"
    details = {}
    if finding.details_json:
        try:
            details = json.loads(finding.details_json)
        except (json.JSONDecodeError, TypeError):
            details = {}
    details["resolved_by"] = "ai_auto_fix"
    details["resolved_at"] = datetime.now(timezone.utc).isoformat()
    finding.details_json = json.dumps(details)
    session.add(finding)
    session.commit()
    cache_delete_pattern(f"{FINDINGS_CACHE_PREFIX}:{current_user.tenant_id}")
    return {"status": "resolved", "finding_id": str(finding.id)}