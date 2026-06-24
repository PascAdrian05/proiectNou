from datetime import datetime, timezone

import redis
from fastapi import HTTPException, Request, status

from app.core.config import settings


_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _client_ip(request: Request) -> str:
    if not request.client:
        return "unknown"
    return request.client.host or "unknown"


def enforce_rate_limit(request: Request, scope: str, limit: int, window_seconds: int) -> None:
    ip = _client_ip(request)
    key = f"ratelimit:{scope}:{ip}"
    current = _client.incr(key)
    if current == 1:
        _client.expire(key, window_seconds)
    if current > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")


def is_login_locked(identity: str) -> bool:
    return _client.exists(f"auth:lock:{identity}") == 1


def register_failed_login(identity: str) -> None:
    fail_key = f"auth:fail:{identity}"
    lock_key = f"auth:lock:{identity}"

    attempts = _client.incr(fail_key)
    if attempts == 1:
        _client.expire(fail_key, settings.auth_fail_window_seconds)

    if attempts >= settings.auth_max_failed_attempts:
        _client.setex(lock_key, settings.auth_lockout_minutes * 60, "1")


def clear_failed_login(identity: str) -> None:
    _client.delete(f"auth:fail:{identity}")
    _client.delete(f"auth:lock:{identity}")
