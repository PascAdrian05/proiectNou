from pydantic import BaseModel, HttpUrl


class CheckoutSessionRequest(BaseModel):
    plan: str
    success_url: HttpUrl | None = None
    cancel_url: HttpUrl | None = None


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class BillingPortalResponse(BaseModel):
    portal_url: str
