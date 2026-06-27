from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Credential(SQLModel, table=True):
    """WebAuthn credential (passkey) stored for a user."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    credential_id: str = Field(index=True, unique=True)  # Base64URL-encoded
    public_key: str  # Base64URL-encoded
    sign_count: int = Field(default=0)
    transports: str | None = Field(default=None, nullable=True)  # JSON array
    device_name: str | None = Field(default=None, nullable=True)  # Friendly name
    created_at: datetime = Field(default_factory=_utcnow)
    last_used_at: datetime | None = Field(default=None, nullable=True)