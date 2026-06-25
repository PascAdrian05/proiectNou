from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


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
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
