import json
import smtplib
import socket
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any
from uuid import UUID

import httpx
from sqlmodel import Session

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


def _check_uptime(url: str) -> dict[str, Any]:
    try:
        response = httpx.get(url, timeout=15.0, follow_redirects=True)
        return {
            "reachable": True,
            "status_code": response.status_code,
            "latency_ms": round(response.elapsed.total_seconds() * 1000, 2),
            "headers": dict(response.headers),
        }
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


def _check_ssl_expiry(domain: str) -> dict[str, Any]:
    context = ssl.create_default_context()
    with socket.create_connection((domain, 443), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname=domain) as tls_sock:
            cert = tls_sock.getpeercert()
            not_after = cert.get("notAfter")
            if not not_after:
                return {"valid": False, "error": "Certificate missing notAfter field"}

            expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days_left = (expiry - datetime.now(timezone.utc)).days
            return {
                "valid": True,
                "expires_at": expiry.isoformat(),
                "days_left": days_left,
            }


def _check_security_headers(headers: dict[str, Any]) -> dict[str, Any]:
    lower_headers = {key.lower(): value for key, value in headers.items()}
    missing = [header for header in SECURITY_HEADERS if header not in lower_headers]
    return {"missing": missing, "score": max(0, 100 - len(missing) * 15)}


def _check_common_ports(domain: str) -> dict[str, Any]:
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


@celery_app.task(name="scan.run_full_scan")
def run_full_scan(scan_run_id: str, website_id: str, url: str, domain: str, tenant_id: str) -> dict[str, Any]:
    scan_run_uuid = UUID(scan_run_id)
    website_uuid = UUID(website_id)
    tenant_uuid = UUID(tenant_id)
    with Session(engine) as session:
        scan_run = session.get(ScanRun, scan_run_uuid)
        website = session.get(Website, website_uuid)
        tenant = session.get(Tenant, tenant_uuid)
        if not scan_run or not website or not tenant:
            return {"status": "failed", "reason": "scan context not found"}

        scan_run.status = "running"
        scan_run.started_at = datetime.now(timezone.utc)
        session.add(scan_run)
        session.commit()

        findings_created: list[dict[str, Any]] = []
        try:
            uptime = _check_uptime(url)
            ssl_result = _check_ssl_expiry(domain)
            headers_result = _check_security_headers(uptime.get("headers", {}))
            ports_result = _check_common_ports(domain)

            checks = {
                "uptime": uptime,
                "ssl_expiry": ssl_result,
                "security_headers": headers_result,
                "open_ports": ports_result,
            }

            for kind, data in checks.items():
                severity = _finding_severity(kind, data)
                needs_finding = (
                    (kind == "uptime" and not data.get("reachable", True))
                    or (kind == "ssl_expiry" and (not data.get("valid", False) or data.get("days_left", 999) <= 30))
                    or (kind == "security_headers" and len(data.get("missing", [])) > 0)
                    or (kind == "open_ports" and len(data.get("open_ports", [])) > 0)
                )
                if not needs_finding:
                    continue

                finding = Finding(
                    tenant_id=tenant.id,
                    website_id=website.id,
                    scan_run_id=scan_run.id,
                    kind=kind,
                    severity=severity,
                    title=f"{kind} issue detected",
                    details_json=json.dumps(data),
                )
                session.add(finding)
                session.flush()
                findings_created.append({"id": finding.id, "severity": severity, "kind": kind, "data": data})

            scan_run.status = "completed"
            scan_run.completed_at = datetime.now(timezone.utc)
            scan_run.result_json = json.dumps(checks)
            website.last_scan_at = datetime.now(timezone.utc)
            session.add(scan_run)
            session.add(website)
            session.commit()

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
                            {
                                "tenant_id": str(tenant.id),
                                "severity": finding["severity"],
                                "kind": finding["kind"],
                                "details": finding["data"],
                            },
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

            session.commit()
            return {"status": "completed", "findings_created": len(findings_created)}
        except Exception as exc:
            scan_run.status = "failed"
            scan_run.completed_at = datetime.now(timezone.utc)
            scan_run.error_message = str(exc)
            session.add(scan_run)
            session.commit()
            return {"status": "failed", "error": str(exc)}
