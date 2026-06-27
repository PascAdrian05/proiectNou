from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StripeEvent(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: str = Field(index=True, unique=True)
    event_type: str = Field(index=True)
    processed: bool = Field(default=False, index=True)
    payload_json: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    processed_at: datetime | None = None
