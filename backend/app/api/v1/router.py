from fastapi import APIRouter

from app.api.v1.endpoints import ai, ai_conversations, alerts, auth, behavior, billing, events, findings, health, oauth, passkeys, presence, realtime, reports, scans, status, tenant, trust, users, websites


api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tenant.router, prefix="/tenant", tags=["tenant"])
api_router.include_router(websites.router, prefix="/websites", tags=["websites"])
api_router.include_router(scans.router, prefix="/scans", tags=["scans"])
api_router.include_router(findings.router, prefix="/findings", tags=["findings"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(presence.router, prefix="/presence", tags=["presence"])
api_router.include_router(behavior.router, prefix="/behavior", tags=["behavior"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(ai_conversations.router, prefix="/ai/conversations", tags=["ai-conversations"])
api_router.include_router(trust.router, prefix="/trust", tags=["trust"])
api_router.include_router(status.router, prefix="/status", tags=["status"])
api_router.include_router(passkeys.router, prefix="/auth", tags=["passkeys"])
api_router.include_router(realtime.router, prefix="", tags=["realtime"])
