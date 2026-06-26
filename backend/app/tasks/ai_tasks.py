"""Celery tasks that run AI analysis on completed scans.

The previous version used ``asyncio.run`` inside Celery to call the async
AI methods. That pattern is fragile: it creates a new event loop per call,
the sync Groq client blocks the worker thread, and any in-flight loop
state is silently destroyed. This module uses the dedicated ``*_sync``
methods on :mod:`app.services.ai_service` and the shared Redis client so
the worker stays healthy.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session, select

from app.core.database import engine
from app.core.redis_client import get_redis
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.scan_run import ScanRun
from app.models.website import Website
from app.services.ai_service import ai_service
from app.tasks.celery_app import celery_app


def _publish_event(channel: str, event: dict) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.publish(channel, json.dumps(event))
    except Exception:
        # Event publishing must never fail the task — callers may not be
        # subscribed.
        pass


@celery_app.task(name="ai.run_post_scan_analysis", bind=True, max_retries=1, default_retry_delay=60)
def run_post_scan_analysis(self, scan_run_id: str, tenant_id: str) -> dict:
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
            context: dict = {}
            if finding.website_id:
                website = session.get(Website, finding.website_id)
                if website:
                    context["website"] = website.domain

            try:
                result = ai_service.analyze_finding_sync(finding_data, context)
                analysis_results.append({"finding_id": str(finding.id), "result": result})

                auto_fix = ai_service.auto_fix_finding_sync(finding_data, context)
                if auto_fix.get("available"):
                    alert = Alert(
                        tenant_id=tenant_uuid,
                        finding_id=finding.id,
                        channel="ai_auto_fix",
                        recipient="dashboard",
                        status="generated",
                    )
                    alert.error_message = json.dumps(
                        {
                            "fix_summary": auto_fix.get("summary", ""),
                            "fix_steps": auto_fix.get("steps", []),
                            "fix_type": auto_fix.get("fix_type", ""),
                            "risk_level": auto_fix.get("risk_level", "medium"),
                            "estimated_effort": auto_fix.get("estimated_effort", 0),
                            "rollback": auto_fix.get("rollback_instructions", ""),
                        }
                    )
                    session.add(alert)
            except Exception:
                analysis_results.append(
                    {"finding_id": str(finding.id), "result": {"available": False}}
                )

        session.commit()

        _publish_event(
            "ai:completed",
            {
                "type": "ai_analysis_completed",
                "scan_run_id": scan_run_id,
                "tenant_id": tenant_id,
                "findings_analyzed": len(analysis_results),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {"status": "completed", "findings_analyzed": len(analysis_results)}