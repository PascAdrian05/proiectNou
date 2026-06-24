from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Website(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    domain: str = Field(index=True)
    url: str
    status: str = "active"
    ownership_verified: bool = False
    scan_frequency_minutes: int = 60
    last_scan_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
