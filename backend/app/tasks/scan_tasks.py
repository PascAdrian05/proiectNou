import json
import smtplib
import socket
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any
from uuid import UUID

import httpx
import redis as sync_redis
from sqlmodel import Session

from app.core.cache import cache_delete_pattern
from app.core.config import settings
from app.core.database import engine
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.scan_run import ScanRun
from app.models.tenant import Tenant
from app.models.website import Website
from app.tasks.celery_app import celery_app

SECURITY_HEADERS = [
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
]
COMMON_PORTS = [21, 22, 3306, 5432]

STEPS = ["uptime", "ssl_expiry", "security_headers", "open_ports"]


def _publish_event(channel: str, event: dict[str, Any]) -> None:
    try:
        r = sync_redis.from_url(settings.redis_url, decode_responses=True)
        r.publish(channel, json.dumps(event))
        r.close()
    except Exception:
        pass


def _update_progress(session: Session, scan_run_id: UUID, step: str | None, status: str, step_status: str | None = None, progress: dict[str, Any] | None = None, tenant_id: str | None = None, user_id: str | None = None) -> None:
    scan_run = session.get(ScanRun, scan_run_id)
    if not scan_run:
        return
    scan_run.current_step = step
    if progress:
        existing = {}
        if scan_run.progress:
            try:
                existing = json.loads(scan_run.progress)
            except (json.JSONDecodeError, TypeError):
                existing = {}
        existing.update(progress)
        if step_status and step:
            if "step_statuses" not in existing:
                existing["step_statuses"] = {}
            existing["step_statuses"][step] = step_status
        scan_run.progress = json.dumps(existing)
    scan_run.status = status
    if status == "running" and not scan_run.started_at:
        scan_run.started_at = datetime.now(timezone.utc)
    session.add(scan_run)
    session.commit()

    _publish_event("scan:progress", {
        "type": "scan_progress",
        "scan_run_id": str(scan_run_id),
        "step": step,
        "status": status,
        "step_status": step_status,
        "progress": progress,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def _perform_uptime_check(url: str) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as c:
            resp = c.get(url)
            return {
                "reachable": True,
                "status_code": resp.status_code,
                "latency_ms": round(resp.elapsed.total_seconds() * 1000, 2),
                "headers": dict(resp.headers),
            }
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


def _perform_ssl_check(domain: str) -> dict[str, Any]:
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as tls_sock:
                cert = tls_sock.getpeercert()
                not_after = cert.get("notAfter")
                if not not_after:
                    return {"valid": False, "error": "Certificate missing notAfter field"}
                expiry = datetime.strptime(not_after.rsplit(" ", 1)[0], "%b %d %H:%M:%S %Y").replace(tzinfo=timezone.utc)
                days_left = (expiry - datetime.now(timezone.utc)).days
                return {"valid": True, "expires_at": expiry.isoformat(), "days_left": days_left}
    except Exception as exc:
        return {"valid": False, "error": str(exc)}


def _perform_headers_check(headers: dict[str, Any]) -> dict[str, Any]:
    lower_headers = {k.lower(): v for k, v in headers.items()}
    missing = [h for h in SECURITY_HEADERS if h not in lower_headers]
    return {"missing": missing, "score": max(0, 100 - len(missing) * 15)}


def _perform_ports_check(domain: str) -> dict[str, Any]:
    open_ports: list[int] = []
    for port in COMMON_PORTS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        try:
            if sock.connect_ex((domain, port)) == 0:
                open_ports.append(port)
        finally:
            sock.close()
    return {"open_ports": open_ports}


def _finding_severity(kind: str, data: dict[str, Any]) -> str:
    if kind == "uptime" and not data.get("reachable", True):
        return "critical"
    if kind == "ssl_expiry":
        if not data.get("valid", False):
            return "high"
        if data.get("days_left", 999) <= 7:
            return "high"
        if data.get("days_left", 999) <= 30:
            return "medium"
    if kind == "security_headers" and len(data.get("missing", [])) >= 3:
        return "medium"
    if kind == "open_ports" and len(data.get("open_ports", [])) > 0:
        return "high"
    return "low"


def _needs_finding(kind: str, data: dict[str, Any]) -> bool:
    if kind == "uptime" and not data.get("reachable", True):
        return True
    if kind == "ssl_expiry":
        if not data.get("valid", False):
            return True
        if data.get("days_left", 999) <= 30:
            return True
    if kind == "security_headers" and len(data.get("missing", [])) > 0:
        return True
    if kind == "open_ports" and len(data.get("open_ports", [])) > 0:
        return True
    return False


def _send_webhook(url: str, payload: dict[str, Any]) -> None:
    httpx.post(url, json=payload, timeout=10.0)


def _send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password or not settings.smtp_from_email:
        raise RuntimeError("SMTP is not fully configured")
    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


def _dispatch_alerts(session: Session, tenant: Tenant, findings_created: list[dict]) -> None:
    for finding in findings_created:
        if tenant.alert_webhook_url:
            alert = Alert(
                tenant_id=tenant.id,
                finding_id=finding["id"],
                channel="webhook",
                recipient=tenant.alert_webhook_url,
            )
            session.add(alert)
            session.flush()
            try:
                _send_webhook(
                    tenant.alert_webhook_url,
                    {"tenant_id": str(tenant.id), "severity": finding["severity"], "kind": finding["kind"], "details": finding["data"]},
                )
                alert.status = "sent"
                alert.sent_at = datetime.now(timezone.utc)
            except Exception as exc:
                alert.status = "failed"
                alert.error_message = str(exc)
            session.add(alert)
        if tenant.alert_email:
            alert = Alert(
                tenant_id=tenant.id,
                finding_id=finding["id"],
                channel="email",
                recipient=tenant.alert_email,
            )
            session.add(alert)
            session.flush()
            try:
                _send_email(
                    tenant.alert_email,
                    "Security finding detected",
                    f"Issue kind: {finding['kind']}\nSeverity: {finding['severity']}\nDetails: {finding['data']}",
                )
                alert.status = "sent"
                alert.sent_at = datetime.now(timezone.utc)
            except Exception as exc:
                alert.status = "failed"
                alert.error_message = str(exc)
            session.add(alert)


@celery_app.task(name="scan.run_full_scan", bind=True, max_retries=2, default_retry_delay=30)
def run_full_scan(self, scan_run_id: str, website_id: str, url: str, domain: str, tenant_id: str, user_id: str | None = None) -> dict[str, Any]:
    import time as _time

    scan_run_uuid = UUID(scan_run_id)
    website_uuid = UUID(website_id)
    tenant_uuid = UUID(tenant_id)

    with Session(engine) as session:
        scan_run = session.get(ScanRun, scan_run_uuid)
        website = session.get(Website, website_uuid)
        tenant = session.get(Tenant, tenant_uuid)
        if not scan_run or not website or not tenant:
            return {"status": "failed", "reason": "scan context not found"}

        _update_progress(session, scan_run_uuid, None, "running", step_status=None, progress={"steps_completed": 0, "total_steps": len(STEPS)}, tenant_id=str(tenant_uuid), user_id=user_id)

    checks: dict[str, dict[str, Any]] = {}
    step_statuses: dict[str, str] = {}
    findings_created: list[dict[str, Any]] = []
    headers_from_uptime: dict[str, Any] = {}

    STEP_MIN_SECONDS = 8  # each step appears to take at least this long on the frontend

    def run_step(step_name: str) -> tuple[str, dict[str, Any], str]:
        t0 = _time.monotonic()
        step_index = STEPS.index(step_name)
        try:
            _publish_event("scan:progress", {
                "type": "scan_progress",
                "scan_run_id": str(scan_run_uuid),
                "step": step_name,
                "status": "running",
                "step_status": "active",
                "progress": {"steps_completed": step_index, "total_steps": len(STEPS), "current_check": step_name, "step_progress": 0},
                "tenant_id": tenant_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            if step_name == "uptime":
                result = _perform_uptime_check(url)
            elif step_name == "ssl_expiry":
                result = _perform_ssl_check(domain)
                if not result.get("valid") and isinstance(result.get("error"), str):
                    err_lower = result["error"].lower()
                    if any(word in err_lower for word in ["refused", "timeout", "connection closed", "no route", "eof occurred", "certificate verify failed"]):
                        result["no_access"] = True
            elif step_name == "security_headers":
                headers_from_uptime_local = headers_from_uptime
                result = _perform_headers_check(headers_from_uptime_local)
            elif step_name == "open_ports":
                result = _perform_ports_check(domain)
                if not result.get("open_ports"):
                    result["no_access"] = True
            else:
                return step_name, {"error": f"unknown step: {step_name}"}, "error"

            elapsed = _time.monotonic() - t0
            if elapsed < STEP_MIN_SECONDS:
                remaining = STEP_MIN_SECONDS - elapsed
                # Publish granular progress every ~1.5s during the wait
                increments = max(1, int(remaining / 1.5))
                for i in range(increments):
                    _time.sleep(remaining / increments)
                    step_progress_pct = min(95, int(((i + 1) / increments) * 100))
                    _publish_event("scan:progress", {
                        "type": "scan_progress",
                        "scan_run_id": str(scan_run_uuid),
                        "step": step_name,
                        "status": "running",
                        "step_status": "active",
                        "progress": {
                            "steps_completed": step_index,
                            "total_steps": len(STEPS),
                            "current_check": step_name,
                            "step_progress": step_progress_pct,
                        },
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            step_status = "no_access" if result.get("no_access") else "success"

            with Session(engine) as step_session:
                _update_progress(step_session, scan_run_uuid, step_name, "running", step_status=step_status, progress={
                    "steps_completed": step_index + 1,
                    "total_steps": len(STEPS),
                    "current_check": step_name,
                    "step_progress": 100,
                }, tenant_id=tenant_id, user_id=user_id)

            return step_name, result, step_status
        except Exception as exc:
            elapsed = _time.monotonic() - t0
            if elapsed < STEP_MIN_SECONDS:
                _time.sleep(STEP_MIN_SECONDS - elapsed)
            return step_name, {"error": str(exc)}, "error"

    try:
        for step_name in STEPS:
            step_name_res, result, step_sts = run_step(step_name)
            checks[step_name_res] = result
            step_statuses[step_name_res] = step_sts
            if step_name_res == "uptime" and result.get("headers"):
                headers_from_uptime = result.get("headers", {})

        with Session(engine) as session:
            if not session.get(ScanRun, scan_run_uuid):
                return {"status": "failed", "error": "ScanRun not found in DB session"}
            
            current_detected_kinds = set()
            for kind, data in checks.items():
                if not _needs_finding(kind, data):
                    continue
                severity = _finding_severity(kind, data)
                finding = Finding(
                    tenant_id=tenant_uuid,
                    website_id=website_uuid,
                    scan_run_id=scan_run_uuid,
                    kind=kind,
                    severity=severity,
                    title=f"{kind} issue detected",
                    details_json=json.dumps(data),
                )
                session.add(finding)
                session.flush()
                findings_created.append({"id": finding.id, "severity": severity, "kind": kind, "data": data})
                current_detected_kinds.add(kind)

            old_findings = session.exec(
                select(Finding).where(
                    Finding.tenant_id == tenant_uuid,
                    Finding.website_id == website_uuid,
                    Finding.status == "open",
                    Finding.id.not_in([f["id"] for f in findings_created]) if findings_created else True,
                )
            ).all()
            for old in old_findings:
                if old.kind not in current_detected_kinds:
                    old.status = "resolved"
                    old.details_json = json.dumps({"resolved_by": "auto", "previous_kind": old.kind, "resolution": "No longer detected"})
                    session.add(old)

            scan_run = session.get(ScanRun, scan_run_uuid)
            website = session.get(Website, website_uuid)
            scan_run.status = "completed"
            scan_run.completed_at = datetime.now(timezone.utc)
            scan_run.result_json = json.dumps(checks)
            scan_run.current_step = None
            scan_run.progress = json.dumps({"steps_completed": len(STEPS), "total_steps": len(STEPS), "current_check": None, "step_statuses": step_statuses})
            website.last_scan_at = datetime.now(timezone.utc)
            session.add(scan_run)
            session.add(website)
            session.commit()

            _dispatch_alerts(session, tenant, findings_created)

            session.commit()

            cache_delete_pattern(f"scanruns:{tenant_id}")
            cache_delete_pattern(f"findings:{tenant_id}")
            cache_delete_pattern(f"alerts:{tenant_id}")

            _publish_event("scan:completed", {
                "type": "scan_completed",
                "scan_run_id": str(scan_run_uuid),
                "website_id": str(website_uuid),
                "tenant_id": str(tenant_uuid),
                "user_id": user_id,
                "status": "completed",
                "findings_count": len(findings_created),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            from app.tasks.ai_tasks import run_post_scan_analysis
            run_post_scan_analysis.delay(str(scan_run_uuid), str(tenant_uuid))

            return {"status": "completed", "findings_created": len(findings_created)}

    except Exception as exc:
        with Session(engine) as session:
            scan_run = session.get(ScanRun, scan_run_uuid)
            if scan_run:
                scan_run.status = "failed"
                scan_run.completed_at = datetime.now(timezone.utc)
                scan_run.error_message = str(exc)
                scan_run.current_step = None
                session.add(scan_run)
                session.commit()

        _publish_event("scan:completed", {
            "type": "scan_completed",
            "scan_run_id": str(scan_run_uuid),
            "tenant_id": str(tenant_uuid),
            "user_id": user_id,
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return {"status": "failed", "error": str(exc)}
