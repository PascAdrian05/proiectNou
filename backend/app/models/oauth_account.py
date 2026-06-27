from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel
import sqlalchemy as sa


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OAuthAccount(SQLModel, table=True):
    __table_args__ = (
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    provider: str = Field(index=True)
    provider_user_id: str = Field(index=True)
    email: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
