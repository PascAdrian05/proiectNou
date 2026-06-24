from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
import asyncio
import json
import time

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.scan_run import ScanRun
from app.models.user import User


router = APIRouter()


@router.get("/scans/stream")
async def stream_scan_updates(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    async def event_generator():
        last_check = time.time()
        try:
            while True:
                # Query recent scan runs for this tenant
                runs = session.exec(
                    select(ScanRun)
                    .where(ScanRun.tenant_id == current_user.tenant_id)
                    .order_by(ScanRun.created_at.desc())
                    .limit(20)
                ).all()

                payload = {
                    "timestamp": time.time(),
                    "runs": [
                        {
                            "id": str(run.id),
                            "status": run.status,
                            "website_id": str(run.website_id),
                            "started_at": run.started_at.isoformat() if run.started_at else None,
                            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                        }
                        for run in runs
                    ],
                }

                yield f"data: {json.dumps(payload)}\n\n"
                last_check = time.time()

                # Send heartbeat every 15 seconds to keep connection alive
                await asyncio.sleep(15)
                yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/alerts/stream")
async def stream_alert_updates(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    async def event_generator():
        try:
            while True:
                alerts = session.exec(
                    select(Alert)
                    .where(Alert.tenant_id == current_user.tenant_id)
                    .order_by(Alert.created_at.desc())
                    .limit(50)
                ).all()

                payload = {
                    "timestamp": time.time(),
                    "alerts": [
                        {
                            "id": str(alert.id),
                            "channel": alert.channel,
                            "recipient": alert.recipient,
                            "status": alert.status,
                            "created_at": alert.created_at.isoformat() if alert.created_at else None,
                            "sent_at": alert.sent_at.isoformat() if alert.sent_at else None,
                        }
                        for alert in alerts
                    ],
                }

                yield f"data: {json.dumps(payload)}\n\n"

                await asyncio.sleep(20)
                yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/findings/stream")
async def stream_finding_updates(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    async def event_generator():
        try:
            while True:
                findings = session.exec(
                    select(Finding)
                    .where(Finding.tenant_id == current_user.tenant_id)
                    .order_by(Finding.created_at.desc())
                    .limit(50)
                ).all()

                payload = {
                    "timestamp": time.time(),
                    "findings": [
                        {
                            "id": str(finding.id),
                            "severity": finding.severity,
                            "kind": finding.kind,
                            "title": finding.title,
                            "website_id": str(finding.website_id),
                            "scan_run_id": str(finding.scan_run_id),
                            "created_at": finding.created_at.isoformat() if finding.created_at else None,
                        }
                        for finding in findings
                    ],
                }

                yield f"data: {json.dumps(payload)}\n\n"

                await asyncio.sleep(20)
                yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
