from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.database import engine
from app.models.scan_run import ScanRun
from app.models.subscription import Subscription
from app.models.website import Website
from app.tasks.celery_app import celery_app


@celery_app.task(name="scan.check_scheduled")
def check_scheduled_scans() -> dict[str, int]:
    from app.tasks.scan_tasks import run_full_scan

    enqueued = 0
    # Use timezone-aware UTC. ``datetime.utcnow()`` returns a naive value
    # which produces inconsistent comparisons against tz-aware columns.
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        websites = session.exec(select(Website)).all()

        for website in websites:
            freq = website.scan_frequency_minutes
            if not freq or freq <= 0:
                continue

            last_scan = website.last_scan_at
            if last_scan and last_scan.tzinfo:
                last_scan = last_scan.replace(tzinfo=None)
            if last_scan and (now - last_scan).total_seconds() < freq * 60:
                continue

            sub = session.exec(
                select(Subscription).where(Subscription.tenant_id == website.tenant_id)
            ).first()

            plan = sub.plan if sub else "free"
            from app.core.plan_limits import PlanLimits
            daily_limit = PlanLimits.get_daily_scan_limit(plan)
            if daily_limit != float("inf") and sub and sub.scans_used >= daily_limit:
                continue

            scan_run = ScanRun(tenant_id=website.tenant_id, website_id=website.id, status="pending")
            session.add(scan_run)
            session.flush()
            session.commit()

            session.refresh(scan_run)
            if not session.get(ScanRun, scan_run.id):
                session.rollback()
                continue

            url = website.url or f"https://{website.domain}"
            run_full_scan.delay(
                scan_run_id=str(scan_run.id),
                website_id=str(website.id),
                url=url,
                domain=website.domain,
                tenant_id=str(website.tenant_id),
                user_id=None,
            )
            enqueued += 1

    return {"scheduled_scans_enqueued": enqueued}
