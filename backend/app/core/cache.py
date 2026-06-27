"""Redis-backed cache helpers.

Why Redis is the only store
----------------------------
The application runs as multiple API workers behind a load balancer and the
scan worker is a separate process. An in-process dict cache means one worker's
cache is invisible to the others, which produces stale results for the user
and "phantom" alerts that disappear when the worker restarts. The previous
implementation carried an in-memory fallback that, in production, masked
Redis outages and silently degraded cross-worker consistency.

The module now treats Redis as the single source of truth. In development
(``ENVIRONMENT == "development"``) the in-memory fallback is kept so a
developer can run the API without Docker. In every other environment a
missing Redis client raises so we fail loud instead of silently shipping
stale data.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import threading
import time
from functools import wraps
from typing import Any, Callable, Optional

from app.core.config import settings
from app.core.redis_client import get_redis


logger = logging.getLogger(__name__)


# Fallback is only used in non-production environments. We never want a
# worker to silently fall back in staging or production.
_USE_FALLBACK = settings.environment.lower() in {"development", "dev", "test"}

_fallback_lock = threading.Lock()
_fallback_store: dict[str, tuple[float, str]] = {}


# --------------------------------------------------------------------------- #
# Fallback (development only)
# --------------------------------------------------------------------------- #


def _fallback_get(key: str) -> Optional[str]:
    now = time.time()
    with _fallback_lock:
        entry = _fallback_store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at and expires_at < now:
            _fallback_store.pop(key, None)
            return None
        return value


def _fallback_set(key: str, value: str, ttl: int) -> None:
    with _fallback_lock:
        _fallback_store[key] = (time.time() + ttl if ttl else 0, value)


def _fallback_delete_pattern(pattern: str) -> None:
    with _fallback_lock:
        for k in [k for k in _fallback_store if fnmatch.fnmatch(k, pattern)]:
            _fallback_store.pop(k, None)


def _fallback_delete(key: str) -> None:
    with _fallback_lock:
        _fallback_store.pop(key, None)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def cache_get(key: str) -> Any | None:
    """Read a JSON-encoded value from Redis (or the dev fallback)."""
    client = get_redis()
    if client is None:
        if not _USE_FALLBACK:
            raise RuntimeError("Redis is required but unavailable")
        raw = _fallback_get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    try:
        val = client.get(key)
    except Exception as exc:
        if not _USE_FALLBACK:
            raise
        logger.warning("cache_get fell back to in-memory store: %s", exc)
        return None
    if not val:
        return None
    if isinstance(val, bytes):
        val = val.decode("utf-8", errors="replace")
    try:
        return json.loads(val)
    except json.JSONDecodeError:
        return None


def cache_set(key: str, value: Any, ttl: int = 30) -> None:
    """Write a JSON-encoded value to Redis (or the dev fallback)."""
    payload = json.dumps(value, default=str)
    client = get_redis()
    if client is None:
        if not _USE_FALLBACK:
            raise RuntimeError("Redis is required but unavailable")
        _fallback_set(key, payload, ttl)
        return
    try:
        client.setex(key, ttl, payload)
    except Exception as exc:
        if not _USE_FALLBACK:
            raise
        logger.warning("cache_set fell back to in-memory store: %s", exc)
        _fallback_set(key, payload, ttl)


def cache_delete_pattern(pattern: str) -> None:
    """Delete every key matching ``pattern``."""
    client = get_redis()
    if client is None:
        if not _USE_FALLBACK:
            raise RuntimeError("Redis is required but unavailable")
        _fallback_delete_pattern(pattern)
        return
    try:
        keys = list(client.scan_iter(match=pattern, count=500))
        if keys:
            client.delete(*keys)
    except Exception as exc:
        if not _USE_FALLBACK:
            raise
        logger.warning("cache_delete_pattern failed: %s", exc)


def cache_delete(key: str) -> None:
    """Delete a single key."""
    client = get_redis()
    if client is None:
        if not _USE_FALLBACK:
            raise RuntimeError("Redis is required but unavailable")
        _fallback_delete(key)
        return
    try:
        client.delete(key)
    except Exception as exc:
        if not _USE_FALLBACK:
            raise
        logger.warning("cache_delete failed: %s", exc)


def cached(ttl: int = 30, prefix: str = "cache") -> Callable:
    """Cache decorator.

    The cache key is built from the first positional argument (typically
    ``tenant_id``). For predictable invalidation, callers should pass the
    tenant as a keyword argument.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tenant_id = kwargs.get("tenant_id") or (args[0] if args else None)
            key = f"{prefix}:{tenant_id}" if tenant_id else f"{prefix}:global"
            cached_val = cache_get(key)
            if cached_val is not None:
                return cached_val
            result = func(*args, **kwargs)
            cache_set(key, result, ttl)
            return result

        return wrapper

    return decorator


def invalidate_tenant_cache(tenant_id: str, *prefixes: str) -> None:
    """Invalidate every cached entry the given tenant owns across ``prefixes``."""
    for prefix in prefixes:
        cache_delete_pattern(f"{prefix}:{tenant_id}")