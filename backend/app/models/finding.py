from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, Index, SQLModel


def _utcnow() -> datetime:
    """Timezone-aware UTC default so naive comparisons never leak in."""
    return datetime.now(timezone.utc)


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
    first_seen_at: datetime = Field(default_factory=_utcnow)
    last_seen_at: datetime = Field(default_factory=_utcnow)

    __table_args__ = (
        # Drives the "open findings for tenant ordered by recency" query
        # used by the dashboard and SSE snapshots.
        Index(
            "ix_finding_tenant_status_first_seen",
            "tenant_id",
            "status",
            "first_seen_at",
        ),
        # The list endpoint filters by tenant + website + status when the
        # user drills into a specific site.
        Index(
            "ix_finding_tenant_website_status",
            "tenant_id",
            "website_id",
            "status",
        ),
        # Severity-filtered queries ("show me critical/high first").
        Index(
            "ix_finding_tenant_severity_status",
            "tenant_id",
            "severity",
            "status",
        ),
    )