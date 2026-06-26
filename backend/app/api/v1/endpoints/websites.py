from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, delete, select
from uuid import UUID

from app.api.deps import get_current_user, require_roles
from app.core.cache import cache_get, cache_set, cache_delete_pattern
from app.core.database import get_session
from app.core.subscription_middleware import check_website_limit
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
    # Check website limit based on subscription plan
    check_website_limit(session, str(current_user.tenant_id))
    
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
    cache_delete_pattern(f"websites:{current_user.tenant_id}")
    return WebsiteRead.model_validate(website)


@router.get("", response_model=list[WebsiteRead])
def list_websites(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[WebsiteRead]:
    tenant_id = str(current_user.tenant_id)
    cached = cache_get(f"websites:{tenant_id}")
    if cached is not None:
        return [WebsiteRead(**item) for item in cached]
    websites = session.exec(select(Website).where(Website.tenant_id == current_user.tenant_id)).all()
    result = [WebsiteRead.model_validate(item) for item in websites]
    cache_set(f"websites:{tenant_id}", [r.model_dump() for r in result], ttl=300)
    return result


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
    cache_delete_pattern(f"websites:{current_user.tenant_id}")
    cache_delete_pattern(f"scanruns:{current_user.tenant_id}")
    cache_delete_pattern(f"findings:{current_user.tenant_id}")
    cache_delete_pattern(f"alerts:{current_user.tenant_id}")
    return {"status": "deleted"}
