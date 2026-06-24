from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, delete, select
from uuid import UUID

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.user import User
from app.schemas.finding import FindingRead


router = APIRouter()


@router.get("", response_model=list[FindingRead])
def list_findings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[FindingRead]:
    findings = session.exec(select(Finding).where(Finding.tenant_id == current_user.tenant_id)).all()
    return [FindingRead.model_validate(item) for item in findings]


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
    return {"status": "deleted"}
