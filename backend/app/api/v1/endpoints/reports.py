from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.behavior_store import compute_behavior_score
from app.core.config import settings
from app.core.database import get_session
from app.core.report_store import create_share_token, get_public_report_snapshot, get_tenant_id_by_token, store_public_report_snapshot
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.scan_run import ScanRun
from app.models.tenant import Tenant
from app.models.user import User
from app.models.website import Website


router = APIRouter()


def _build_report_payload(session: Session, tenant_id: str, user_id: str) -> dict[str, object]:
    tenant = session.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    websites = session.exec(select(Website).where(Website.tenant_id == tenant_id)).all()
    findings = session.exec(select(Finding).where(Finding.tenant_id == tenant_id)).all()
    alerts = session.exec(select(Alert).where(Alert.tenant_id == tenant_id)).all()
    scans = session.exec(select(ScanRun).where(ScanRun.tenant_id == tenant_id)).all()

    website_items = []
    for website in websites:
        related_findings = [finding for finding in findings if str(finding.website_id) == str(website.id)]
        severity_score = 100 - sum(
            30 if finding.severity == "critical" else 20 if finding.severity == "high" else 10 if finding.severity == "medium" else 4
            for finding in related_findings
        )
        website_items.append(
            {
                "id": str(website.id),
                "domain": website.domain,
                "url": website.url,
                "score": max(0, min(100, severity_score)),
                "status": website.status,
                "last_scan_at": website.last_scan_at.isoformat() if website.last_scan_at else None,
                "finding_count": len(related_findings),
            }
        )

    score = round(sum(item["score"] for item in website_items) / len(website_items)) if website_items else 100

    recent_findings = sorted(findings, key=lambda item: item.last_seen_at, reverse=True)[:5]
    recent_alerts = sorted(alerts, key=lambda item: item.created_at, reverse=True)[:5]
    recent_scans = sorted(scans, key=lambda item: item.created_at, reverse=True)[:10]
    behavior = compute_behavior_score(str(tenant_id), str(user_id))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": str(tenant_id),
        "branding": {
            "tenant_name": tenant.name if tenant else "Tenant",
            "brand_name": tenant.brand_name if tenant and tenant.brand_name else (tenant.name if tenant else "Security Monitor"),
            "brand_logo_url": tenant.brand_logo_url if tenant else None,
            "report_primary_color": tenant.report_primary_color if tenant and tenant.report_primary_color else "#c74634",
            "report_cta_text": tenant.report_cta_text if tenant and tenant.report_cta_text else "Request Full Access",
            "report_cta_url": tenant.report_cta_url if tenant and tenant.report_cta_url else settings.frontend_url,
            "report_base_url": tenant.report_base_url if tenant and tenant.report_base_url else settings.frontend_url,
        },
        "security_score": score,
        "behavior_risk": behavior,
        "websites": website_items,
        "top_findings": [
            {
                "id": str(finding.id),
                "website_id": str(finding.website_id),
                "kind": finding.kind,
                "severity": finding.severity,
                "title": finding.title,
                "status": finding.status,
                "last_seen_at": finding.last_seen_at.isoformat(),
            }
            for finding in recent_findings
        ],
        "alerts": [
            {
                "id": str(alert.id),
                "finding_id": str(alert.finding_id),
                "channel": alert.channel,
                "recipient": alert.recipient,
                "status": alert.status,
                "sent_at": alert.sent_at.isoformat() if alert.sent_at else None,
                "created_at": alert.created_at.isoformat(),
            }
            for alert in recent_alerts
        ],
        "scan_runs": [
            {
                "id": str(scan.id),
                "website_id": str(scan.website_id),
                "status": scan.status,
                "started_at": scan.started_at.isoformat() if scan.started_at else None,
                "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
                "created_at": scan.created_at.isoformat(),
            }
            for scan in recent_scans
        ],
    }


@router.post("/share")
def create_report_share(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    share = create_share_token(str(current_user.tenant_id))
    payload = _build_report_payload(session, str(current_user.tenant_id), str(current_user.id))
    store_public_report_snapshot(share["token"], payload)
    base_url = str(payload["branding"].get("report_base_url") or settings.frontend_url).rstrip("/")
    return {
        "share_token": share["token"],
        "share_url": f"{base_url}/public/report/{share['token']}",
        "expires_at": share["expires_at"],
    }


@router.get("/public/{share_token}")
def read_public_report(share_token: str) -> dict[str, object]:
    tenant_id = get_tenant_id_by_token(share_token)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Report link expired or not found")

    snapshot = get_public_report_snapshot(share_token)
    if snapshot:
        return snapshot

    raise HTTPException(status_code=404, detail="Report snapshot not found")