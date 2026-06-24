from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Finding(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    website_id: UUID = Field(foreign_key="website.id", index=True)
    scan_run_id: UUID = Field(foreign_key="scanrun.id", index=True)
    kind: str = Field(index=True)
    severity: str = Field(index=True)
    title: str
    details_json: str | None = None
    status: str = Field(default="open", index=True)
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
