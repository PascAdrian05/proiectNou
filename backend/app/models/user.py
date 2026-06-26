import json
from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4

from sqlmodel import Column, Field, SQLModel, String


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    role: str = Field(default="owner", index=True)
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # 2FA fields
    totp_secret: str | None = Field(default=None, nullable=True)
    totp_enabled: bool = Field(default=False)
    # Backup codes (stored as JSON array of hashes)
    backup_codes: str | None = Field(default=None, sa_column=Column(String))
    # Security setup flag
    security_setup_completed: bool = Field(default=False)
    # Passkeys / WebAuthn
    passkey_enabled: bool = Field(default=False)

    def get_backup_codes_list(self) -> List[str]:
        if not self.backup_codes:
            return []
        return json.loads(self.backup_codes)

    def set_backup_codes_list(self, codes: List[str]) -> None:
        self.backup_codes = json.dumps(codes)
