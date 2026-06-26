from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Subscription(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", index=True, unique=True)
    plan: str = Field(default="free")
    status: str = Field(default="inactive")
    stripe_customer_id: str | None = Field(default=None, index=True)
    stripe_subscription_id: str | None = Field(default=None, index=True)
    current_period_end: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Scan limit tracking
    scans_used: int = Field(default=0)
    scans_limit: int = Field(default=10)  # Free plan: 10 scans per day
    scan_limit_reset_at: datetime | None = Field(default=None)
