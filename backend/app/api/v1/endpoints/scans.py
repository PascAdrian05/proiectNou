from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, delete, select
from uuid import UUID

from app.api.deps import get_current_user
from app.core.cache import cache_get, cache_set, cache_delete_pattern
from app.core.database import get_session
from app.core.plan_limits import PlanLimits
from app.core.subscription_middleware import check_scan_frequency, get_user_plan
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.scan_run import ScanRun
from app.models.subscription import Subscription
from app.models.user import User
from app.models.website import Website
from app.schemas.scan import ScanJobResponse, ScanRequest, ScanRunRead
from app.tasks.scan_tasks import run_full_scan


router = APIRouter()


@router.post("/enqueue", response_model=ScanJobResponse)
def enqueue_scan(
    payload: ScanRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ScanJobResponse:
    website = session.exec(
        select(Website).where(Website.id == payload.website_id, Website.tenant_id == current_user.tenant_id)
    ).first()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    # Get user's subscription
    subscription = session.exec(
        select(Subscription).where(Subscription.tenant_id == current_user.tenant_id)
    ).first()
    
    if not subscription:
        subscription = Subscription(tenant_id=current_user.tenant_id, plan="free", status="active")
        session.add(subscription)
        session.commit()
        session.refresh(subscription)

    # Check and reset scan limit if needed (24 hour reset)
    now = datetime.now(timezone.utc)
    if subscription.scan_limit_reset_at and now >= subscription.scan_limit_reset_at:
        subscription.scans_used = 0
        subscription.scan_limit_reset_at = None
        session.add(subscription)
        session.commit()

    # Check scan count limit based on subscription plan
    plan = subscription.plan or "free"
    can_scan_count, count_error = PlanLimits.can_scan_by_count(plan, subscription.scans_used, subscription.scans_limit)
    if not can_scan_count:
        raise HTTPException(status_code=429, detail=count_error)

    # Check scan frequency limit based on subscription plan
    last_scan = session.exec(
        select(ScanRun)
        .where(ScanRun.website_id == website.id, ScanRun.status == "completed")
        .order_by(ScanRun.created_at.desc())
    ).first()
    
    if last_scan and last_scan.created_at:
        hours_since_last_scan = (datetime.now(timezone.utc) - last_scan.created_at).total_seconds() / 3600
        check_scan_frequency(session, str(current_user.tenant_id), int(hours_since_last_scan))

    # Increment scan count and set reset time if first scan of the day
    subscription.scans_used += 1
    if subscription.scans_used == 1:
        subscription.scan_limit_reset_at = now + timedelta(hours=24)
    session.add(subscription)
    session.commit()

    scan_run = ScanRun(tenant_id=current_user.tenant_id, website_id=website.id, status="pending")
    session.add(scan_run)
    session.commit()
    session.refresh(scan_run)

    task = run_full_scan.delay(str(scan_run.id), str(website.id), website.url, website.domain, str(current_user.tenant_id), str(current_user.id))
    scan_run.celery_task_id = task.id
    session.add(scan_run)
    session.commit()
    cache_delete_pattern(f"scanruns:{current_user.tenant_id}")

    return ScanJobResponse(task_id=task.id, scan_run_id=scan_run.id)


@router.get("/runs", response_model=list[ScanRunRead])
def list_scan_runs(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
    website_id: Optional[UUID] = Query(None),
) -> list[ScanRunRead]:
    """List recent scan runs for the current tenant.

    Keyset pagination keeps the response bounded regardless of how much
    history the tenant has accumulated. The default 50 is enough for the
    ScansPage UI without forcing the client to aggregate.
    """
    tenant_id = str(current_user.tenant_id)
    cache_key = f"scanruns:{tenant_id}:{limit}:{cursor or ''}:{website_id or ''}"
    cached = cache_get(cache_key)
    if cached is not None:
        return [ScanRunRead(**item) for item in cached]

    query = select(ScanRun).where(ScanRun.tenant_id == current_user.tenant_id)
    if website_id:
        query = query.where(ScanRun.website_id == website_id)
    if cursor:
        cursor_ts, _, cursor_id = cursor.partition("|")
        try:
            cursor_dt = datetime.fromisoformat(cursor_ts)
            cursor_uuid = UUID(cursor_id)
            query = query.where(
                (ScanRun.created_at < cursor_dt)
                | ((ScanRun.created_at == cursor_dt) & (ScanRun.id < cursor_uuid))
            )
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid cursor")

    query = query.order_by(ScanRun.created_at.desc(), ScanRun.id.desc()).limit(limit)
    runs = session.exec(query).all()
    result = [ScanRunRead.model_validate(run) for run in runs]
    cache_set(cache_key, [r.model_dump() for r in result], ttl=300)
    return result


@router.get("/limits")
def get_scan_limits(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get current scan limit status for the user."""
    subscription = session.exec(
        select(Subscription).where(Subscription.tenant_id == current_user.tenant_id)
    ).first()
    
    if not subscription:
        subscription = Subscription(tenant_id=current_user.tenant_id, plan="free", status="active")
        session.add(subscription)
        session.commit()
        session.refresh(subscription)

    # Check and reset scan limit if needed
    now = datetime.now(timezone.utc)
    if subscription.scan_limit_reset_at and now >= subscription.scan_limit_reset_at:
        subscription.scans_used = 0
        subscription.scan_limit_reset_at = None
        session.add(subscription)
        session.commit()

    plan = subscription.plan or "free"
    daily_limit = PlanLimits.get_daily_scan_limit(plan)
    
    return {
        "plan": plan,
        "scans_used": subscription.scans_used,
        "scans_limit": daily_limit if daily_limit != float('inf') else -1,  # -1 for unlimited
        "scan_limit_reset_at": subscription.scan_limit_reset_at.isoformat() if subscription.scan_limit_reset_at else None,
        "can_scan": subscription.scans_used < daily_limit if daily_limit != float('inf') else True,
        "remaining_scans": max(0, daily_limit - subscription.scans_used) if daily_limit != float('inf') else -1,
    }


@router.delete("/history")
def delete_scan_history(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    scan_runs = session.exec(select(ScanRun).where(ScanRun.tenant_id == current_user.tenant_id)).all()
    deleted_count = 0

    for scan_run in scan_runs:
        finding_ids = session.exec(select(Finding.id).where(Finding.scan_run_id == scan_run.id)).all()
        if finding_ids:
            session.exec(delete(Alert).where(Alert.finding_id.in_(finding_ids)))
        session.exec(delete(Finding).where(Finding.scan_run_id == scan_run.id))
        session.delete(scan_run)
        deleted_count += 1

    session.commit()
    cache_delete_pattern(f"scanruns:{current_user.tenant_id}")
    cache_delete_pattern(f"findings:{current_user.tenant_id}")
    cache_delete_pattern(f"alerts:{current_user.tenant_id}")
    return {"deleted_scan_runs": deleted_count}


@router.delete("/{scan_run_id}")
def delete_scan_run(
    scan_run_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    scan_run = session.exec(select(ScanRun).where(ScanRun.id == scan_run_id, ScanRun.tenant_id == current_user.tenant_id)).first()
    if not scan_run:
        raise HTTPException(status_code=404, detail="Scan run not found")

    finding_ids = session.exec(select(Finding.id).where(Finding.scan_run_id == scan_run.id)).all()
    if finding_ids:
        session.exec(delete(Alert).where(Alert.finding_id.in_(finding_ids)))
    session.exec(delete(Finding).where(Finding.scan_run_id == scan_run.id))
    session.delete(scan_run)
    session.commit()
    cache_delete_pattern(f"scanruns:{current_user.tenant_id}")
    cache_delete_pattern(f"findings:{current_user.tenant_id}")
    cache_delete_pattern(f"alerts:{current_user.tenant_id}")
    return {"status": "deleted"}
