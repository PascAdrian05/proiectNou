import json
from typing import Any, Callable
from functools import wraps

import redis as sync_redis
from app.core.config import settings


def _get_redis():
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


def cache_get(key: str) -> Any | None:
    try:
        r = _get_redis()
        val = r.get(key)
        r.close()
        if val:
            return json.loads(val)
    except Exception:
        pass
    return None


def cache_set(key: str, value: Any, ttl: int = 30) -> None:
    try:
        r = _get_redis()
        r.setex(key, ttl, json.dumps(value, default=str))
        r.close()
    except Exception:
        pass


def cache_delete_pattern(pattern: str) -> None:
    try:
        r = _get_redis()
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
        r.close()
    except Exception:
        pass


def cached(ttl: int = 30, prefix: str = "cache") -> Callable:
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
