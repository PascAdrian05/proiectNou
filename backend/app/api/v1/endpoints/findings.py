from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, delete, select
from uuid import UUID

from app.api.deps import get_current_user
from app.core.cache import cache_get, cache_set, cache_delete_pattern
from app.core.database import get_session
from datetime import datetime, timezone
import json

from app.models.alert import Alert
from app.models.finding import Finding
from app.models.user import User
from app.schemas.finding import FindingRead


router = APIRouter()
FINDINGS_CACHE_PREFIX = "findings"


@router.get("", response_model=list[FindingRead])
def list_findings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[FindingRead]:
    tenant_id = str(current_user.tenant_id)
    cached = cache_get(f"{FINDINGS_CACHE_PREFIX}:{tenant_id}")
    if cached is not None:
        return [FindingRead(**item) for item in cached]
    findings = session.exec(select(Finding).where(Finding.tenant_id == current_user.tenant_id)).all()
    result = [FindingRead.model_validate(item) for item in findings]
    cache_set(f"{FINDINGS_CACHE_PREFIX}:{tenant_id}", [r.model_dump() for r in result], ttl=30)
    return result


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
