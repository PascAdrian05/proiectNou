from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from app.api.deps import get_current_user, oauth2_scheme
from app.core.database import get_session
from app.core.security import decode_token
from app.core.token_store import is_token_revoked
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.scan_run import ScanRun
from app.models.user import User
from app.schemas.auth import TokenPayload


def _resolve_user_from_token(token: str, session: Session) -> User | None:
    """Resolve user from either header or query param token."""
    try:
        payload = decode_token(token)
        token_data = TokenPayload(sub=payload.get("sub"))
        if token_data.sub is None or payload.get("type") != "access":
            return None
        jti = payload.get("jti")
        if not jti or is_token_revoked(jti):
            return None
        user_id = UUID(token_data.sub)
        return session.exec(select(User).where(User.id == user_id)).first()
    except Exception:
        return None


router = APIRouter()
executor = ThreadPoolExecutor(max_workers=4)


def _get_scan_runs_sync(session: Session, tenant_id: str) -> list:
    """Sync DB call for scan runs."""
    return session.exec(
        select(ScanRun)
        .where(ScanRun.tenant_id == tenant_id)
        .order_by(ScanRun.created_at.desc())
        .limit(20)
    ).all()


def _get_alerts_sync(session: Session, tenant_id: str) -> list:
    """Sync DB call for alerts."""
    return session.exec(
        select(Alert)
        .where(Alert.tenant_id == tenant_id)
        .order_by(Alert.created_at.desc())
        .limit(50)
    ).all()


def _get_findings_sync(session: Session, tenant_id: str) -> list:
    """Sync DB call for findings."""
    return session.exec(
        select(Finding)
        .where(Finding.tenant_id == tenant_id)
        .order_by(Finding.created_at.desc())
        .limit(50)
    ).all()


async def _resolve_current_user(
    session: Session = Depends(get_session),
    token: str = Depends(oauth2_scheme),
    token_query: str | None = Query(None, alias="token"),
):
    """Resolve current user from header or query param token (for EventSource support)."""
    actual_token = token if token and token != "undefined" else (token_query if token_query and token_query != "undefined" else None)
    if not actual_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # First try header-based token
    try:
        user = get_current_user(session=session, token=actual_token)
        if user:
            return user
    except Exception:
        pass
    
    # Fallback to query param token resolution
    user = _resolve_user_from_token(actual_token, session)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    return user


@router.get("/scans/stream")
async def stream_scan_updates(
    session: Session = Depends(get_session),
    current_user: User = Depends(_resolve_current_user),
):
    async def event_generator():
        last_check = time.time()
        try:
            while True:
                # Run sync DB query in threadpool to avoid blocking event loop
                runs = await asyncio.get_event_loop().run_in_executor(
                    executor, _get_scan_runs_sync, session, str(current_user.tenant_id)
                )

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
    current_user: User = Depends(_resolve_current_user),
):
    async def event_generator():
        try:
            while True:
                alerts = await asyncio.get_event_loop().run_in_executor(
                    executor, _get_alerts_sync, session, str(current_user.tenant_id)
                )

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
    current_user: User = Depends(_resolve_current_user),
):
    async def event_generator():
        try:
            while True:
                findings = await asyncio.get_event_loop().run_in_executor(
                    executor, _get_findings_sync, session, str(current_user.tenant_id)
                )

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
