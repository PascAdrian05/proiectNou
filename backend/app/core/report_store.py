import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import redis

from app.core.config import settings


_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

REPORT_SHARE_TTL_SECONDS = 7 * 24 * 60 * 60


def create_share_token(tenant_id: str) -> dict[str, str]:
    token = secrets.token_urlsafe(24)
    _client.setex(f"report:share:{token}", REPORT_SHARE_TTL_SECONDS, tenant_id)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=REPORT_SHARE_TTL_SECONDS)
    return {"token": token, "expires_at": expires_at.isoformat()}


def get_tenant_id_by_token(token: str) -> str | None:
    tenant_id = _client.get(f"report:share:{token}")
    return tenant_id or None


def store_public_report_snapshot(token: str, payload: dict[str, Any]) -> None:
    _client.setex(f"report:snapshot:{token}", REPORT_SHARE_TTL_SECONDS, json.dumps(payload))


def get_public_report_snapshot(token: str) -> dict[str, Any] | None:
    raw = _client.get(f"report:snapshot:{token}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None