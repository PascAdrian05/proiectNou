"""Token revocation and presence tracking helpers backed by the shared Redis
client. The previous implementation used a process-local client which meant
revocations did not propagate between workers.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import settings
from app.core.redis_client import get_redis


PRESENCE_TTL_SECONDS = 90


def revoke_token_jti(jti: str, exp_timestamp: int) -> None:
    client = get_redis()
    if client is None:
        return
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = max(1, exp_timestamp - now)
    try:
        client.setex(f"revoked:{jti}", ttl, "1")
    except Exception:
        pass


def is_token_revoked(jti: str) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return client.exists(f"revoked:{jti}") == 1
    except Exception:
        return False


def mark_user_online(tenant_id: str, user_id: str, ttl_seconds: int = PRESENCE_TTL_SECONDS) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.setex(f"presence:{tenant_id}:{user_id}", ttl_seconds, "1")
    except Exception:
        pass


def mark_user_offline(tenant_id: str, user_id: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.delete(f"presence:{tenant_id}:{user_id}")
    except Exception:
        pass


def count_online_users(tenant_id: str) -> int:
    client = get_redis()
    if client is None:
        return 0
    pattern = f"presence:{tenant_id}:*"
    try:
        return sum(1 for _ in client.scan_iter(match=pattern, count=500))
    except Exception:
        return 0