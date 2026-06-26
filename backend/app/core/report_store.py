"""Public report share-link persistence backed by the shared Redis client.

The previous implementation created a Redis client at import time. If Redis
was down at startup the whole process crashed before serving any request.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.core.redis_client import get_redis


REPORT_SHARE_TTL_SECONDS = 7 * 24 * 60 * 60


def _client():
    return get_redis()


def create_share_token(tenant_id: str) -> Optional[dict[str, str]]:
    client = _client()
    if client is None:
        return None
    token = secrets.token_urlsafe(24)
    try:
        client.setex(f"report:share:{token}", REPORT_SHARE_TTL_SECONDS, tenant_id)
    except Exception:
        return None
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=REPORT_SHARE_TTL_SECONDS)
    return {"token": token, "expires_at": expires_at.isoformat()}


def get_tenant_id_by_token(token: str) -> Optional[str]:
    client = _client()
    if client is None:
        return None
    try:
        return client.get(f"report:share:{token}")
    except Exception:
        return None


def store_public_report_snapshot(token: str, payload: dict[str, Any]) -> bool:
    client = _client()
    if client is None:
        return False
    try:
        client.setex(f"report:snapshot:{token}", REPORT_SHARE_TTL_SECONDS, json.dumps(payload))
        return True
    except Exception:
        return False


def get_public_report_snapshot(token: str) -> Optional[dict[str, Any]]:
    client = _client()
    if client is None:
        return None
    try:
        raw = client.get(f"report:snapshot:{token}")
    except Exception:
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None