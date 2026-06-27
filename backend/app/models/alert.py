from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, Index, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Alert(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    finding_id: UUID = Field(foreign_key="finding.id", index=True)
    channel: str = Field(index=True)
    recipient: str
    status: str = Field(default="pending", index=True)
    error_message: str | None = None
    sent_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        # List alerts ordered by recency for tenant.
        Index("ix_alert_tenant_created_at", "tenant_id", "created_at"),
        # Retry queries: "find failed webhook alerts".
        Index("ix_alert_tenant_status", "tenant_id", "status"),
    )