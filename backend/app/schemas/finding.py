from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FindingRead(BaseModel):
    id: UUID
    tenant_id: UUID
    website_id: UUID
    scan_run_id: UUID
    kind: str
    severity: str
    title: str
    details_json: str | None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)
