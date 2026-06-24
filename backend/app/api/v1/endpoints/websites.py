from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, delete, select
from uuid import UUID

from app.api.deps import get_current_user, require_roles
from app.core.database import get_session
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.scan_run import ScanRun
from app.models.user import User
from app.models.website import Website
from app.schemas.website import WebsiteCreate, WebsiteRead


router = APIRouter()


@router.post("", response_model=WebsiteRead, status_code=status.HTTP_201_CREATED)
def create_website(
    payload: WebsiteCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("owner", "admin", "analyst")),
) -> WebsiteRead:
    existing = session.exec(
        select(Website).where(Website.tenant_id == current_user.tenant_id, Website.domain == payload.domain)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Website already exists for this tenant")

    website = Website(
        tenant_id=current_user.tenant_id,
        domain=payload.domain,
        url=str(payload.url),
        scan_frequency_minutes=payload.scan_frequency_minutes,
    )
    session.add(website)
    session.commit()
    session.refresh(website)
    return WebsiteRead.model_validate(website)


@router.get("", response_model=list[WebsiteRead])
def list_websites(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[WebsiteRead]:
    websites = session.exec(select(Website).where(Website.tenant_id == current_user.tenant_id)).all()
    return [WebsiteRead.model_validate(item) for item in websites]


@router.delete("/{website_id}")
def delete_website(
    website_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("owner", "admin", "analyst")),
) -> dict[str, str]:
    website = session.exec(select(Website).where(Website.id == website_id, Website.tenant_id == current_user.tenant_id)).first()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    finding_ids = session.exec(select(Finding.id).where(Finding.website_id == website.id)).all()
    if finding_ids:
        session.exec(delete(Alert).where(Alert.finding_id.in_(finding_ids)))

    session.exec(delete(Finding).where(Finding.website_id == website.id))
    session.exec(delete(ScanRun).where(ScanRun.website_id == website.id))
    session.delete(website)
    session.commit()
    return {"status": "deleted"}
