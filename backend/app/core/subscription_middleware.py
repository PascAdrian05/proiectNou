from fastapi import HTTPException, Request, status
from sqlmodel import Session, select

from app.core.plan_limits import PlanLimits
from app.models.subscription import Subscription
from app.models.website import Website


def get_user_plan(session: Session, tenant_id: str) -> str:
    """Get the current plan for a tenant."""
    subscription = session.exec(
        select(Subscription).where(Subscription.tenant_id == tenant_id)
    ).first()
    return subscription.plan if subscription else PlanLimits.FREE


def check_plan_feature(session: Session, tenant_id: str, feature: str) -> None:
    """Check if the tenant's plan has access to a specific feature."""
    plan = get_user_plan(session, tenant_id)
    if not PlanLimits.has_feature(plan, feature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Feature '{feature}' is not available in your {plan} plan. Upgrade to access this feature."
        )


def check_website_limit(session: Session, tenant_id: str) -> None:
    """Check if the tenant can add more websites."""
    plan = get_user_plan(session, tenant_id)
    current_count = session.exec(
        select(Website).where(Website.tenant_id == tenant_id)
    ).count()
    
    can_add, message = PlanLimits.can_add_website(plan, current_count)
    if not can_add:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )


def check_scan_frequency(session: Session, tenant_id: str, last_scan_hours_ago: int) -> None:
    """Check if the tenant can perform a scan based on frequency limits."""
    plan = get_user_plan(session, tenant_id)
    can_scan, message = PlanLimits.can_scan(plan, last_scan_hours_ago)
    if not can_scan:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message
        )


def require_feature(feature: str):
    """Dependency to require a specific feature for the endpoint."""
    def dependency(session: Session, tenant_id: str):
        check_plan_feature(session, tenant_id, feature)
    return dependency
