from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_session
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantSettingsRead, TenantSettingsUpdate
from app.tasks.scan_tasks import _send_email, _send_webhook


router = APIRouter()


@router.get("/settings", response_model=TenantSettingsRead)
def read_tenant_settings(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> TenantSettingsRead:
    tenant = session.get(Tenant, current_user.tenant_id)
    return TenantSettingsRead(
        name=tenant.name,
        alert_email=tenant.alert_email,
        alert_webhook_url=tenant.alert_webhook_url,
        brand_name=tenant.brand_name,
        brand_logo_url=tenant.brand_logo_url,
        report_primary_color=tenant.report_primary_color,
        report_base_url=tenant.report_base_url,
        report_cta_text=tenant.report_cta_text,
        report_cta_url=tenant.report_cta_url,
    )


@router.patch("/settings")
def update_tenant_settings(
    payload: TenantSettingsUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> dict[str, str]:
    tenant = session.get(Tenant, current_user.tenant_id)
    if payload.alert_email is not None:
        tenant.alert_email = str(payload.alert_email)
    if payload.alert_webhook_url is not None:
        tenant.alert_webhook_url = str(payload.alert_webhook_url)
    if payload.brand_name is not None:
        tenant.brand_name = payload.brand_name
    if payload.brand_logo_url is not None:
        tenant.brand_logo_url = str(payload.brand_logo_url)
    if payload.report_primary_color is not None:
        tenant.report_primary_color = payload.report_primary_color
    if payload.report_base_url is not None:
        tenant.report_base_url = str(payload.report_base_url)
    if payload.report_cta_text is not None:
        tenant.report_cta_text = payload.report_cta_text
    if payload.report_cta_url is not None:
        tenant.report_cta_url = str(payload.report_cta_url)
    session.add(tenant)
    session.commit()
    return {"status": "updated"}


@router.post("/settings/test-alert")
def send_test_alert(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("owner", "admin")),
) -> dict[str, str]:
    tenant = session.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if not tenant.alert_email and not tenant.alert_webhook_url:
        raise HTTPException(status_code=400, detail="Configure alert email or webhook first")

    subject = "Security Monitor — test alert"
    body = (
        "This is a test alert from Security Monitor.\n\n"
        "If you received this, your notification channel is configured correctly.\n"
        "You'll be notified automatically when a scan finds a security issue."
    )
    payload = {
        "type": "test_alert",
        "tenant_id": str(tenant.id),
        "message": "Test alert from Security Monitor",
    }

    errors: list[str] = []
    sent = 0

    if tenant.alert_email:
        try:
            _send_email(str(tenant.alert_email), subject, body)
            sent += 1
        except Exception as exc:
            errors.append(f"email: {exc}")

    if tenant.alert_webhook_url:
        try:
            _send_webhook(str(tenant.alert_webhook_url), payload)
            sent += 1
        except Exception as exc:
            errors.append(f"webhook: {exc}")

    if sent == 0:
        # No channel succeeded — surface the per-channel failures so the
        # caller can fix the config.
        raise HTTPException(
            status_code=502,
            detail="; ".join(errors) if errors else "Alert delivery failed",
        )

    # Partial success — return the status plus per-channel details so the
    # UI can tell the user which channel(s) failed.
    return {
        "status": "sent" if not errors else "partial",
        "sent": sent,
        "errors": errors,
    }
