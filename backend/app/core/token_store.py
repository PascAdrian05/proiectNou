from datetime import datetime, timezone

import redis

from app.core.config import settings


_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

PRESENCE_TTL_SECONDS = 90


def _presence_key(tenant_id: str, user_id: str) -> str:
    return f"presence:{tenant_id}:{user_id}"


def revoke_token_jti(jti: str, exp_timestamp: int) -> None:
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = max(1, exp_timestamp - now)
    _client.setex(f"revoked:{jti}", ttl, "1")


def is_token_revoked(jti: str) -> bool:
    return _client.exists(f"revoked:{jti}") == 1


def mark_user_online(tenant_id: str, user_id: str, ttl_seconds: int = PRESENCE_TTL_SECONDS) -> None:
    _client.setex(_presence_key(tenant_id, user_id), ttl_seconds, "1")


def mark_user_offline(tenant_id: str, user_id: str) -> None:
    _client.delete(_presence_key(tenant_id, user_id))


def count_online_users(tenant_id: str) -> int:
    pattern = f"presence:{tenant_id}:*"
    return sum(1 for _ in _client.scan_iter(match=pattern))
