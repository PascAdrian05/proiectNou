from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AlertRead(BaseModel):
    id: UUID
    finding_id: UUID
    channel: str
    recipient: str
    status: str
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
