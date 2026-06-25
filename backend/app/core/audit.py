import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import Request
from sqlmodel import Session

from app.models.audit_log import AuditLog


def log_action(
    session: Session,
    user_id: UUID,
    tenant_id: UUID,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    request: Optional[Request] = None,
    success: bool = True,
    details: Optional[dict] = None,
) -> AuditLog:
    """Log an audit action."""
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
    
    audit_log = AuditLog(
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        details=json.dumps(details) if details else None,
        created_at=datetime.now(timezone.utc),
    )
    
    session.add(audit_log)
    session.commit()
    session.refresh(audit_log)
    
    return audit_log


def get_user_audit_logs(
    session: Session,
    user_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    """Get audit logs for a specific user."""
    from sqlmodel import select
    
    statement = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    return list(session.exec(statement).all())


def get_tenant_audit_logs(
    session: Session,
    tenant_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    """Get audit logs for a specific tenant."""
    from sqlmodel import select
    
    statement = (
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    return list(session.exec(statement).all())
