"""Shared Redis client with connection pooling and graceful fallback.

A single client is created lazily on first use. If Redis is unreachable,
``get_redis()`` returns ``None`` so callers can decide how to degrade.
"""

from __future__ import annotations

import threading
from typing import Optional

import redis

from app.core.config import settings


_pool: Optional[redis.ConnectionPool] = None
_client: Optional[redis.Redis] = None
_lock = threading.Lock()


def _build_pool() -> Optional[redis.ConnectionPool]:
    if not settings.redis_url:
        return None
    try:
        return redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            max_connections=64,
        )
    except Exception:
        return None


def get_redis() -> Optional[redis.Redis]:
    """Return a shared Redis client, building the pool lazily.

    Returns ``None`` if Redis cannot be reached. Callers must handle the
    "no Redis" case explicitly — typically by degrading to in-memory state.
    """
    global _client
    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client

        pool = _build_pool()
        if pool is None:
            return None

        try:
            client = redis.Redis(connection_pool=pool)
            client.ping()
            _client = client
            return _client
        except Exception:
            return None


def redis_available() -> bool:
    """Cheap probe for whether Redis is reachable in the current process."""
    return get_redis() is not None