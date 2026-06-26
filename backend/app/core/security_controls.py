"""Rate-limit and account-lockout helpers backed by the shared Redis client.

All functions degrade gracefully — if Redis is unreachable the rate limit
becomes a no-op (the API still works) and failed-login tracking is dropped.
A previous version of this module eagerly created a Redis client at import
time, which crashed the whole app if Redis was unreachable.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.redis_client import get_redis


# In-memory fallback for rate-limit counters (best-effort, per-process).
_local_lock = threading.Lock()
_local_counters: dict[str, tuple[float, int]] = {}


def _client_ip(request: Request) -> str:
    if not request.client:
        return "unknown"
    return request.client.host or "unknown"


def _local_incr(key: str, window_seconds: int) -> int:
    now = time.time()
    with _local_lock:
        expires_at, count = _local_counters.get(key, (0.0, 0))
        if expires_at <= now:
            expires_at = now + window_seconds
            count = 0
        count += 1
        _local_counters[key] = (expires_at, count)
        return count


def _local_get(key: str) -> int:
    now = time.time()
    with _local_lock:
        entry = _local_counters.get(key)
        if not entry:
            return 0
        expires_at, count = entry
        if expires_at <= now:
            _local_counters.pop(key, None)
            return 0
        return count


def enforce_rate_limit(request: Request, scope: str, limit: int, window_seconds: int) -> None:
    ip = _client_ip(request)
    key = f"ratelimit:{scope}:{ip}"

    client = get_redis()
    if client is None:
        current = _local_incr(key, window_seconds)
    else:
        try:
            current = client.incr(key)
            if current == 1:
                client.expire(key, window_seconds)
        except Exception:
            current = _local_incr(key, window_seconds)

    if current > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
        )


def is_login_locked(identity: str) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return client.exists(f"auth:lock:{identity}") == 1
    except Exception:
        return False


def register_failed_login(identity: str) -> None:
    client = get_redis()
    if client is None:
        return
    fail_key = f"auth:fail:{identity}"
    lock_key = f"auth:lock:{identity}"
    try:
        attempts = client.incr(fail_key)
        if attempts == 1:
            client.expire(fail_key, settings.auth_fail_window_seconds)
        if attempts >= settings.auth_max_failed_attempts:
            client.setex(lock_key, settings.auth_lockout_minutes * 60, "1")
    except Exception:
        # Tracking failure must not break the login endpoint.
        pass


def clear_failed_login(identity: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.delete(f"auth:fail:{identity}")
        client.delete(f"auth:lock:{identity}")
    except Exception:
        pass