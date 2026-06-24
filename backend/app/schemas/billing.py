from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubscriptionRead(BaseModel):
    plan: str
    status: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    current_period_end: datetime | None

    model_config = ConfigDict(from_attributes=True)
