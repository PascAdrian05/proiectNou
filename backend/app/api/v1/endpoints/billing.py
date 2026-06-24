from datetime import datetime, timezone
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_session
from app.models.stripe_event import StripeEvent
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.billing_checkout import BillingPortalResponse, CheckoutSessionRequest, CheckoutSessionResponse
from app.schemas.billing import SubscriptionRead


router = APIRouter()

if settings.stripe_api_key:
    stripe.api_key = settings.stripe_api_key


@router.get("/subscription", response_model=SubscriptionRead)
def get_subscription(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SubscriptionRead:
    subscription = session.exec(
        select(Subscription).where(Subscription.tenant_id == current_user.tenant_id)
    ).first()
    if not subscription:
        subscription = Subscription(tenant_id=current_user.tenant_id, plan="free", status="active")
        session.add(subscription)
        session.commit()
        session.refresh(subscription)

    return SubscriptionRead.model_validate(subscription)


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=stripe_signature, secret=settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc

    data = event.get("data", {}).get("object", {})
    event_type = event.get("type")
    event_id = event.get("id")

    event_row = None
    if event_id:
        event_row = session.exec(select(StripeEvent).where(StripeEvent.event_id == event_id)).first()
        if event_row and event_row.processed:
            return {"received": "true"}
        if not event_row:
            event_row = StripeEvent(
                event_id=event_id,
                event_type=event_type or "unknown",
                processed=False,
                payload_json=payload.decode("utf-8", errors="ignore"),
            )
            session.add(event_row)
            session.commit()
            session.refresh(event_row)

    try:
        if event_type == "checkout.session.completed":
            customer_id = data.get("customer")
            tenant_id = data.get("client_reference_id")
            if tenant_id:
                try:
                    tenant_uuid = UUID(tenant_id)
                except (TypeError, ValueError):
                    tenant_uuid = None

                subscription = None
                if tenant_uuid:
                    subscription = session.exec(select(Subscription).where(Subscription.tenant_id == tenant_uuid)).first()
                if subscription:
                    subscription.stripe_customer_id = customer_id
                    subscription.status = "active"
                    session.add(subscription)
                    session.commit()

        if event_type in {"customer.subscription.created", "customer.subscription.updated"}:
            customer_id = data.get("customer")
            stripe_subscription_id = data.get("id")
            status_value = data.get("status", "active")
            current_period_end = data.get("current_period_end")

            subscription = session.exec(
                select(Subscription).where(Subscription.stripe_customer_id == customer_id)
            ).first()
            if subscription:
                subscription.status = status_value
                subscription.stripe_subscription_id = stripe_subscription_id
                if current_period_end:
                    subscription.current_period_end = datetime.fromtimestamp(current_period_end, tz=timezone.utc)
                session.add(subscription)
                session.commit()

        if event_type in {"customer.subscription.deleted"}:
            customer_id = data.get("customer")
            subscription = session.exec(
                select(Subscription).where(Subscription.stripe_customer_id == customer_id)
            ).first()
            if subscription:
                subscription.status = "canceled"
                session.add(subscription)
                session.commit()

        if event_row:
            event_row.processed = True
            event_row.processed_at = datetime.now(timezone.utc)
            session.add(event_row)
            session.commit()
    except Exception as exc:
        if event_row:
            event_row.error_message = str(exc)
            session.add(event_row)
            session.commit()
        raise

    return {"received": "true"}


@router.post("/stripe/checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    payload: CheckoutSessionRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CheckoutSessionResponse:
    if not settings.stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe API key not configured")

    plan_to_price = {
        "basic": settings.stripe_price_basic_id,
        "pro": settings.stripe_price_pro_id,
    }
    price_id = plan_to_price.get(payload.plan.lower())
    if not price_id:
        raise HTTPException(status_code=400, detail="Unsupported plan or missing Stripe price id")

    subscription = session.exec(
        select(Subscription).where(Subscription.tenant_id == current_user.tenant_id)
    ).first()
    if not subscription:
        subscription = Subscription(tenant_id=current_user.tenant_id, plan="free", status="active")
        session.add(subscription)
        session.commit()
        session.refresh(subscription)

    success_url = str(payload.success_url or f"{settings.frontend_url}/?billing=success")
    cancel_url = str(payload.cancel_url or f"{settings.frontend_url}/?billing=cancel")

    checkout_params = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(current_user.tenant_id),
    }
    if subscription.stripe_customer_id:
        checkout_params["customer"] = subscription.stripe_customer_id
    else:
        checkout_params["customer_email"] = current_user.email

    checkout = stripe.checkout.Session.create(**checkout_params)

    return CheckoutSessionResponse(checkout_url=checkout.url, session_id=checkout.id)


@router.post("/stripe/portal", response_model=BillingPortalResponse)
def create_billing_portal(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BillingPortalResponse:
    if not settings.stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe API key not configured")

    subscription = session.exec(
        select(Subscription).where(Subscription.tenant_id == current_user.tenant_id)
    ).first()
    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer found for this tenant")

    portal = stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url=f"{settings.frontend_url}/?billing=portal",
    )
    return BillingPortalResponse(portal_url=portal.url)
