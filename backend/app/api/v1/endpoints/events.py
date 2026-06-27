"""Server-Sent Events endpoints for real-time updates.

Security model
--------------
``EventSource`` cannot set custom request headers, so historically this code
accepted the access JWT via the ``?token=...`` query string. URLs end up in
proxy access logs, browser history, the ``Referer`` header on cross-page
navigations, and screenshots — which leaks long-lived credentials.

Instead we use a single-use *ticket*:

1. The client POSTs the bearer access token to ``/events/ticket`` and receives
   a 60-second, one-shot ``ticket`` UUID.
2. The client opens ``GET /events/{namespace}/stream?ticket=...``.
3. The server consumes the ticket (atomic ``GETDEL``) and accepts the SSE
   connection. A ticket cannot be replayed.

The Redis client is shared via :mod:`app.core.redis_client` so the same
ticket issued on the API container is consumable on every worker that shares
the database — no in-memory dict leaks across processes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.database import get_session
from app.core.redis_client import get_redis
from app.core.security import decode_token
from app.core.token_store import is_token_revoked
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.scan_run import ScanRun
from app.models.user import User
from app.schemas.auth import TokenPayload


logger = logging.getLogger(__name__)

router = APIRouter()
executor = ThreadPoolExecutor(max_workers=4)

# Ticket validity in seconds — long enough for the EventSource to be opened,
# short enough to bound any leak.
SSE_TICKET_TTL_SECONDS = 60


# --------------------------------------------------------------------------- #
# Ticket helpers
# --------------------------------------------------------------------------- #


def _issue_ticket(tenant_id: str, user_id: str) -> str:
    """Persist a single-use SSE ticket in Redis and return its id.

    Tickets are an authentication credential — if we cannot store them
    centrally, we cannot validate them later. We fail closed in that case
    rather than handing out an unbacked token.
    """
    client = get_redis()
    if client is None:
        logger.error("Refusing to issue SSE ticket: Redis is unavailable")
        raise HTTPException(status_code=503, detail="Realtime stream temporarily unavailable")
    ticket = secrets.token_urlsafe(32)
    try:
        client.setex(
            f"sse:ticket:{ticket}",
            SSE_TICKET_TTL_SECONDS,
            json.dumps({"tenant_id": tenant_id, "user_id": user_id}),
        )
    except Exception:
        logger.exception("Failed to persist SSE ticket to Redis")
        raise HTTPException(status_code=503, detail="Realtime stream temporarily unavailable")
    return ticket


def _consume_ticket(ticket: str) -> dict | None:
    """Atomically read-and-delete a ticket. Returns the payload, or None.

    If Redis is unavailable we fail closed (return ``None``) because we
    have no way to validate that a ticket is real — letting unauthenticated
    SSE connections through in that state would be a serious security
    regression.
    """
    if not ticket:
        return None
    client = get_redis()
    if client is None:
        logger.error("Refusing to consume SSE ticket: Redis is unavailable")
        return None
    try:
        # GETDEL is available in Redis 6.2+ which matches our 7.x image.
        raw = client.execute_command("GETDEL", f"sse:ticket:{ticket}")
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        return json.loads(raw)
    except Exception:
        logger.warning("Failed to consume SSE ticket from Redis", exc_info=True)
        return None


# --------------------------------------------------------------------------- #
# User resolution helpers
# --------------------------------------------------------------------------- #


def _resolve_user_from_token(token: str, session: Session) -> User | None:
    """Resolve a user from a raw access token (used by ticket flows)."""
    try:
        payload = decode_token(token)
    except Exception:
        return None
    if payload.get("type") != "access":
        return None
    sub = payload.get("sub")
    jti = payload.get("jti")
    if not sub or not jti or is_token_revoked(jti):
        return None
    try:
        user_id = UUID(sub)
    except (TypeError, ValueError):
        return None
    return session.exec(select(User).where(User.id == user_id)).first()


# --------------------------------------------------------------------------- #
# Database snapshot helpers (sync, run in a worker thread)
# --------------------------------------------------------------------------- #


def _get_scan_runs_sync(session: Session, tenant_id: str) -> list:
    return session.exec(
        select(ScanRun)
        .where(ScanRun.tenant_id == tenant_id)
        .order_by(ScanRun.created_at.desc())
        .limit(20)
    ).all()


def _get_alerts_sync(session: Session, tenant_id: str) -> list:
    return session.exec(
        select(Alert)
        .where(Alert.tenant_id == tenant_id)
        .order_by(Alert.created_at.desc())
        .limit(50)
    ).all()


def _get_findings_sync(session: Session, tenant_id: str) -> list:
    return session.exec(
        select(Finding)
        .where(Finding.tenant_id == tenant_id)
        .order_by(Finding.first_seen_at.desc())
        .limit(50)
    ).all()


# --------------------------------------------------------------------------- #
# Ticket issuance
# --------------------------------------------------------------------------- #


class SSETicketResponse(BaseModel):
    ticket: str
    expires_in: int


@router.post("/ticket", response_model=SSETicketResponse)
def issue_sse_ticket(
    current_user: User = Depends(get_current_user),
) -> SSETicketResponse:
    """Exchange a bearer access token for a single-use SSE ticket."""
    ticket = _issue_ticket(str(current_user.tenant_id), str(current_user.id))
    return SSETicketResponse(ticket=ticket, expires_in=SSE_TICKET_TTL_SECONDS)


def _resolve_ticket_user(ticket: str | None, session: Session) -> User:
    """Resolve the user backing an SSE ticket; raise 401 if invalid."""
    payload = _consume_ticket(ticket)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired SSE ticket")
    user_id = payload.get("user_id")
    tenant_id = payload.get("tenant_id")
    user = session.get(User, UUID(user_id)) if user_id else None
    if not user or str(user.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=401, detail="Invalid SSE ticket subject")
    return user


# --------------------------------------------------------------------------- #
# Streams
# --------------------------------------------------------------------------- #


async def _redis_subscriber(event_queue: asyncio.Queue, stop_event: threading.Event, tenant_id_str: str) -> None:
    """Forward Redis pub/sub messages for this tenant onto an asyncio queue."""
    client = get_redis()
    if client is None:
        return
    pubsub = None
    try:
        pubsub = client.pubsub()
        pubsub.subscribe("scan:progress", "scan:completed", "ai:completed")
        loop = asyncio.get_event_loop()
        for message in pubsub.listen():
            if stop_event.is_set():
                break
            if message.get("type") != "message":
                continue
            try:
                payload = json.loads(message["data"])
            except (json.JSONDecodeError, TypeError):
                continue
            if payload.get("tenant_id") == tenant_id_str:
                asyncio.run_coroutine_threadsafe(
                    event_queue.put(("redis", message["data"])), loop
                )
    except Exception:
        logger.exception("Redis subscriber crashed; SSE will rely on snapshots only")
    finally:
        try:
            if pubsub is not None:
                pubsub.close()
        except Exception:
            pass


def _snapshot_payload(namespace: str, runs, alerts, findings) -> dict:
    """Build the snapshot dict for a given namespace."""
    ts = time.time()
    if namespace == "scans":
        return {
            "timestamp": ts,
            "runs": [
                {
                    "id": str(run.id),
                    "status": run.status,
                    "current_step": run.current_step,
                    "progress": run.progress,
                    "website_id": str(run.website_id),
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                }
                for run in runs
            ],
        }
    if namespace == "alerts":
        return {
            "timestamp": ts,
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
    return {
        "timestamp": ts,
        "findings": [
            {
                "id": str(finding.id),
                "severity": finding.severity,
                "kind": finding.kind,
                "title": finding.title,
                "website_id": str(finding.website_id),
                "scan_run_id": str(finding.scan_run_id),
                "first_seen_at": finding.first_seen_at.isoformat() if finding.first_seen_at else None,
            }
            for finding in findings
        ],
    }


@router.get("/{namespace}/stream")
async def stream_updates(
    namespace: str,
    ticket: str | None = Query(None, alias="ticket"),
    session: Session = Depends(get_session),
):
    """Subscribe to a real-time stream of scan/alert/finding updates."""
    if namespace not in {"scans", "alerts", "findings"}:
        raise HTTPException(status_code=404, detail="Unknown stream namespace")

    current_user = _resolve_ticket_user(ticket, session)
    tenant_id_str = str(current_user.tenant_id)

    async def event_generator():
        event_queue: asyncio.Queue = asyncio.Queue()
        stop_event = threading.Event()

        listener_thread = threading.Thread(
            target=lambda: asyncio.run(_redis_subscriber(event_queue, stop_event, tenant_id_str))
            if False
            else _run_subscriber_in_loop(event_queue, stop_event, tenant_id_str),
            daemon=True,
        )
        listener_thread.start()

        last_db_poll = 0.0
        last_heartbeat = 0.0

        try:
            while True:
                try:
                    source, data = await asyncio.wait_for(event_queue.get(), timeout=2.0)
                    if source == "redis":
                        yield f"data: {data}\n\n"
                        continue
                except asyncio.TimeoutError:
                    pass

                now = time.time()
                if now - last_db_poll >= 3.0:
                    runs = alerts = findings = []
                    if namespace == "scans":
                        runs = await asyncio.get_event_loop().run_in_executor(
                            executor, _get_scan_runs_sync, session, tenant_id_str
                        )
                    elif namespace == "alerts":
                        alerts = await asyncio.get_event_loop().run_in_executor(
                            executor, _get_alerts_sync, session, tenant_id_str
                        )
                    else:
                        findings = await asyncio.get_event_loop().run_in_executor(
                            executor, _get_findings_sync, session, tenant_id_str
                        )
                    payload = _snapshot_payload(namespace, runs, alerts, findings)
                    yield f"data: {json.dumps(payload)}\n\n"
                    last_db_poll = now

                if now - last_heartbeat >= 15:
                    yield ": heartbeat\n\n"
                    last_heartbeat = now
        except asyncio.CancelledError:
            pass
        finally:
            stop_event.set()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            # Never leak this URL via the Referer header on follow-up navs.
            "Referrer-Policy": "no-referrer",
        },
    )


def _run_subscriber_in_loop(event_queue: asyncio.Queue, stop_event: threading.Event, tenant_id_str: str) -> None:
    """Bridge sync Redis pubsub onto the asyncio queue from a worker thread."""
    client = get_redis()
    if client is None:
        return
    pubsub = None
    try:
        pubsub = client.pubsub()
        pubsub.subscribe("scan:progress", "scan:completed", "ai:completed")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for message in pubsub.listen():
            if stop_event.is_set():
                break
            if message.get("type") != "message":
                continue
            try:
                payload = json.loads(message["data"])
            except (json.JSONDecodeError, TypeError):
                continue
            if payload.get("tenant_id") == tenant_id_str:
                asyncio.run_coroutine_threadsafe(
                    event_queue.put(("redis", message["data"])), loop
                )
        loop.close()
    except Exception:
        logger.exception("Redis subscriber crashed; SSE will rely on snapshots only")
    finally:
        try:
            if pubsub is not None:
                pubsub.close()
        except Exception:
            pass