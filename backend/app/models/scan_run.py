from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
