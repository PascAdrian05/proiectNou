from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from uuid import UUID

from app.api.deps import get_current_user
from app.core.database import get_session
from app.core.subscription_middleware import check_plan_feature
from app.models.finding import Finding
from app.models.website import Website
from app.models.user import User
from app.services.ai_service import ai_service


router = APIRouter()


@router.get("/status")
def ai_status(current_user: User = Depends(get_current_user)):
    return {
        "available": ai_service.is_available(),
        "model": "llama-3.3-70b-versatile" if ai_service.is_available() else None,
    }


@router.post("/analyze-finding/{finding_id}")
async def analyze_finding(
    finding_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Check if user's plan has access to AI insights
    check_plan_feature(session, str(current_user.tenant_id), "ai_insights")
    
    finding = session.get(Finding, finding_id)
    if not finding:
        return {"available": False, "message": "Finding not found"}

    finding_data = {
        "id": finding.id,
        "title": finding.title,
        "severity": finding.severity,
        "kind": finding.kind,
        "details_json": finding.details_json,
        "status": finding.status,
    }

    context = {}
    if finding.website_id:
        website = session.get(Website, finding.website_id)
        if website:
            context["website"] = website.domain

    return await ai_service.analyze_finding(finding_data, context)


@router.post("/security-tips")
async def get_security_tips(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Check if user's plan has access to AI insights
    check_plan_feature(session, str(current_user.tenant_id), "ai_insights")
    
    websites = session.exec(select(Website).where(Website.tenant_id == current_user.tenant_id)).all()
    findings = session.exec(select(Finding).where(Finding.tenant_id == current_user.tenant_id)).all()

    website_data = [{"id": w.id, "domain": w.domain} for w in websites]
    finding_data = [
        {
            "id": f.id,
            "severity": f.severity,
            "kind": f.kind,
            "title": f.title,
        }
        for f in findings
    ]

    return await ai_service.get_security_tips(website_data, finding_data)


@router.post("/verify-posture")
async def verify_posture(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Check if user's plan has access to AI insights
    check_plan_feature(session, str(current_user.tenant_id), "ai_insights")
    
    websites = session.exec(select(Website).where(Website.tenant_id == current_user.tenant_id)).all()
    findings = session.exec(select(Finding).where(Finding.tenant_id == current_user.tenant_id)).all()

    website_data = [{"id": w.id, "domain": w.domain} for w in websites]
    finding_data = [
        {
            "id": f.id,
            "severity": f.severity,
            "kind": f.kind,
            "title": f.title,
        }
        for f in findings
    ]

    return await ai_service.verify_security_posture(website_data, finding_data)


@router.post("/proactive-insights")
async def get_proactive_insights(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate proactive AI insights based on current security posture."""
    # Check if user's plan has access to AI insights
    check_plan_feature(session, str(current_user.tenant_id), "ai_insights")
    
    websites = session.exec(select(Website).where(Website.tenant_id == current_user.tenant_id)).all()
    findings = session.exec(select(Finding).where(Finding.tenant_id == current_user.tenant_id, Finding.status == "open")).all()

    website_data = [{"id": w.id, "domain": w.domain} for w in websites]
    finding_data = [
        {
            "id": f.id,
            "severity": f.severity,
            "kind": f.kind,
            "title": f.title,
            "first_seen_at": f.first_seen_at.isoformat() if f.first_seen_at else None,
        }
        for f in findings
    ]

    # Generate insights focused on actionable recommendations
    return await ai_service.get_proactive_insights(website_data, finding_data)


@router.post("/auto-fix/{finding_id}")
async def auto_fix_finding(
    finding_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    check_plan_feature(session, str(current_user.tenant_id), "ai_insights")

    finding = session.get(Finding, finding_id)
    if not finding:
        return {"available": False, "message": "Finding not found"}

    finding_data = {
        "id": str(finding.id),
        "title": finding.title,
        "severity": finding.severity,
        "kind": finding.kind,
        "details_json": finding.details_json,
        "status": finding.status,
    }

    context = {}
    if finding.website_id:
        website = session.get(Website, finding.website_id)
        if website:
            context["website"] = website.domain

    return await ai_service.auto_fix_finding(finding_data, context)
