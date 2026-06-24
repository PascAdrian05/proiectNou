from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from uuid import UUID

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertRead


router = APIRouter()


@router.get("", response_model=list[AlertRead])
def list_alerts(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AlertRead]:
    alerts = session.exec(select(Alert).where(Alert.tenant_id == current_user.tenant_id)).all()
    return [AlertRead.model_validate(item) for item in alerts]


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
    return {"status": "deleted"}
