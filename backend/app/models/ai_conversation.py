from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AIConversation(SQLModel, table=True):
    __tablename__ = "ai_conversation"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    conversation_type: str = Field(index=True)  # e.g., "security_tips", "posture_verification", "finding_analysis"
    messages: str = Field(default="[]")  # JSON string of conversation messages
    context_data: str = Field(default="{}")  # JSON string of additional context
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)