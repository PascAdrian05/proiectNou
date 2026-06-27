from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    """Timezone-aware UTC default — keeps ``created_at`` comparable to
    other tz-aware columns (alerts, scans, events) without surprises."""
    return datetime.now(timezone.utc)


class Tenant(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    alert_email: str | None = None
    alert_webhook_url: str | None = None
    brand_name: str | None = None
    brand_logo_url: str | None = None
    report_primary_color: str | None = None
    report_base_url: str | None = None
    report_cta_text: str | None = None
    report_cta_url: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
