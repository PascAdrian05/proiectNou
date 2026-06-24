from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl


class WebsiteCreate(BaseModel):
    domain: str
    url: HttpUrl
    scan_frequency_minutes: int = 60


class WebsiteRead(BaseModel):
    id: UUID
    domain: str
    url: str
    status: str
    ownership_verified: bool
    scan_frequency_minutes: int
    last_scan_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
