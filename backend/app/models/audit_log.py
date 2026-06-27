from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, Index, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    action: str = Field(index=True)  # e.g., "login", "logout", "2fa_enabled", "website_created", "scan_run"
    resource_type: str | None = Field(default=None, index=True)  # e.g., "user", "website", "scan"
    resource_id: str | None = Field(default=None)  # ID of the resource affected
    ip_address: str | None = Field(default=None)
    user_agent: str | None = Field(default=None)
    success: bool = Field(default=True)
    details: str | None = Field(default=None)  # JSON string for additional context
    created_at: datetime = Field(default_factory=_utcnow, index=True)
    __table_args__ = (
        # "Recent activity for tenant" — the default dashboard query.
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        # "All actions by user" — the user-profile timeline.
        Index("ix_audit_user_created", "user_id", "created_at"),
    )
