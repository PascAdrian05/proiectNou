from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, Index, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScanRun(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    website_id: UUID = Field(foreign_key="website.id", index=True)
    celery_task_id: str | None = Field(default=None, index=True)
    status: str = Field(default="pending", index=True)
    current_step: str | None = None
    progress: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    result_json: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        # "Recent scans for tenant" (SSE snapshot + dashboard).
        Index("ix_scanrun_tenant_created_at", "tenant_id", "created_at"),
        # "Per-website scan history".
        Index("ix_scanrun_tenant_website_created", "tenant_id", "website_id", "created_at"),
    )