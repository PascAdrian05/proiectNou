from datetime import datetime, timezone

import redis

from app.core.config import settings


_client: redis.Redis | None = None
PRESENCE_TTL_SECONDS = 90


def _get_client() -> redis.Redis | None:
    global _client
    if _client is None and settings.redis_url:
        try:
            _client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
            _client.ping()
        except Exception:
            _client = None
    return _client


def _presence_key(tenant_id: str, user_id: str) -> str:
    return f"presence:{tenant_id}:{user_id}"


def revoke_token_jti(jti: str, exp_timestamp: int) -> None:
    client = _get_client()
    if not client:
        return
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = max(1, exp_timestamp - now)
    client.setex(f"revoked:{jti}", ttl, "1")


def is_token_revoked(jti: str) -> bool:
    client = _get_client()
    if not client:
        return False
    return client.exists(f"revoked:{jti}") == 1


def mark_user_online(tenant_id: str, user_id: str, ttl_seconds: int = PRESENCE_TTL_SECONDS) -> None:
    client = _get_client()
    if not client:
        return
    client.setex(_presence_key(tenant_id, user_id), ttl_seconds, "1")


def mark_user_offline(tenant_id: str, user_id: str) -> None:
    client = _get_client()
    if not client:
        return
    client.delete(_presence_key(tenant_id, user_id))


def count_online_users(tenant_id: str) -> int:
    client = _get_client()
    if not client:
        return 0
    pattern = f"presence:{tenant_id}:*"
    return sum(1 for _ in client.scan_iter(match=pattern))
