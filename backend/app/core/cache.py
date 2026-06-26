"""Redis-backed cache helpers with in-memory fallback.

All operations are non-fatal: if Redis is unreachable, the call is a no-op.
This module no longer opens new Redis connections per call — it shares a
single pooled client via :mod:`app.core.redis_client`.
"""

from __future__ import annotations

import json
import threading
from functools import wraps
from typing import Any, Callable, Optional

from app.core.config import settings
from app.core.redis_client import get_redis


_fallback_lock = threading.Lock()
_fallback_store: dict[str, tuple[float, str]] = {}


def _fallback_get(key: str) -> Optional[str]:
    import time

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
    import time

    with _fallback_lock:
        _fallback_store[key] = (time.time() + ttl if ttl else 0, value)


def _fallback_delete_pattern(pattern: str) -> None:
    import fnmatch

    with _fallback_lock:
        keys = [k for k in _fallback_store if fnmatch.fnmatch(k, pattern)]
        for k in keys:
            _fallback_store.pop(k, None)


def cache_get(key: str) -> Any | None:
    client = get_redis()
    if client is None:
        raw = _fallback_get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None
    try:
        val = client.get(key)
    except Exception:
        return None
    if not val:
        return None
    try:
        return json.loads(val)
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl: int = 30) -> None:
    payload = json.dumps(value, default=str)
    client = get_redis()
    if client is None:
        _fallback_set(key, payload, ttl)
        return
    try:
        client.setex(key, ttl, payload)
    except Exception:
        _fallback_set(key, payload, ttl)


def cache_delete_pattern(pattern: str) -> None:
    client = get_redis()
    if client is None:
        _fallback_delete_pattern(pattern)
        return
    try:
        # ``scan_iter`` is O(N) without blocking the server like ``keys``.
        keys = list(client.scan_iter(match=pattern, count=500))
        if keys:
            client.delete(*keys)
    except Exception:
        # Don't try the fallback here — partial state across two stores
        # is worse than a transient miss.
        pass


def cache_delete(key: str) -> None:
    client = get_redis()
    if client is None:
        with _fallback_lock:
            _fallback_store.pop(key, None)
        return
    try:
        client.delete(key)
    except Exception:
        pass


def cached(ttl: int = 30, prefix: str = "cache") -> Callable:
    """Cache decorator. Resolves the cache key from the first positional arg
    (typically ``tenant_id``)."""

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
    for prefix in prefixes:
        cache_delete_pattern(f"{prefix}:{tenant_id}")