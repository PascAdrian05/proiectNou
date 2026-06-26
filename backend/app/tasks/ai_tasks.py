import json
from uuid import UUID

import redis as sync_redis
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import engine
from app.models.finding import Finding
from app.models.alert import Alert
from app.models.scan_run import ScanRun
from app.models.website import Website
from app.services.ai_service import ai_service
from app.tasks.celery_app import celery_app


def _publish_event(channel: str, event: dict) -> None:
    try:
        r = sync_redis.from_url(settings.redis_url, decode_responses=True)
        r.publish(channel, json.dumps(event))
        r.close()
    except Exception:
        pass


@celery_app.task(name="ai.run_post_scan_analysis", bind=True, max_retries=1, default_retry_delay=60)
def run_post_scan_analysis(self, scan_run_id: str, tenant_id: str) -> dict:
    import asyncio

    scan_run_uuid = UUID(scan_run_id)
    tenant_uuid = UUID(tenant_id)

    with Session(engine) as session:
        scan_run = session.get(ScanRun, scan_run_uuid)
        if not scan_run or scan_run.status != "completed":
            return {"status": "skipped", "reason": "scan not completed"}

        findings = session.exec(
            select(Finding).where(Finding.scan_run_id == scan_run_uuid)
        ).all()

        analysis_results = []
        for finding in findings:
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
            try:
                result = asyncio.run(ai_service.analyze_finding(finding_data, context))
                analysis_results.append({"finding_id": str(finding.id), "result": result})

                auto_fix = asyncio.run(ai_service.auto_fix_finding(finding_data, context))
                if auto_fix.get("available"):
                    alert = Alert(
                        tenant_id=tenant_uuid,
                        finding_id=finding.id,
                        channel="ai_auto_fix",
                        recipient="dashboard",
                        status="generated",
                    )
                    alert.error_message = json.dumps({
                        "fix_summary": auto_fix.get("summary", ""),
                        "fix_steps": auto_fix.get("steps", []),
                        "fix_type": auto_fix.get("fix_type", ""),
                        "risk_level": auto_fix.get("risk_level", "medium"),
                        "estimated_effort": auto_fix.get("estimated_effort", 0),
                        "rollback": auto_fix.get("rollback_instructions", ""),
                    })
                    session.add(alert)
            except Exception:
                analysis_results.append({"finding_id": str(finding.id), "result": {"available": False}})

        session.commit()

        _publish_event("ai:completed", {
            "type": "ai_analysis_completed",
            "scan_run_id": scan_run_id,
            "tenant_id": tenant_id,
            "findings_analyzed": len(analysis_results),
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        })

        return {"status": "completed", "findings_analyzed": len(analysis_results)}
