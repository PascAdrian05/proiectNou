from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Alert(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    finding_id: UUID = Field(foreign_key="finding.id", index=True)
    channel: str = Field(index=True)
    recipient: str
    status: str = Field(default="pending", index=True)
    error_message: str | None = None
    sent_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
