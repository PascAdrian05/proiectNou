import time

import redis as sync_redis
from app.core.config import settings


class RedisRateLimiter:
    def __init__(self):
        self._client: sync_redis.Redis | None = None
        self._fallback: InMemoryRateLimiter | None = None

    def _get_client(self) -> sync_redis.Redis | None:
        if self._client is None and settings.redis_url:
            try:
                self._client = sync_redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
                self._client.ping()
            except Exception:
                self._client = None
        return self._client

    def _get_fallback(self) -> "InMemoryRateLimiter":
        if self._fallback is None:
            self._fallback = InMemoryRateLimiter()
        return self._fallback

    def check(self, key: str, max_requests: int | None = None, window_seconds: int = 60) -> tuple[bool, int]:
        if not settings.rate_limit_enabled:
            return True, 0
        client = self._get_client()
        if client is None:
            return self._get_fallback().check(key, max_requests, window_seconds)
        limit = max_requests or settings.rate_limit_per_minute
        now = int(time.time())
        window_start = now - window_seconds
        try:
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window_seconds)
            _, current_count, _, _ = pipe.execute()
            if current_count >= limit:
                oldest = client.zrange(key, 0, 0, withscores=True)
                retry_after = int(oldest[0][1] + window_seconds - now) if oldest else window_seconds
                return False, max(1, retry_after)
            return True, 0
        except Exception:
            return self._get_fallback().check(key, max_requests, window_seconds)


class InMemoryRateLimiter:
    def __init__(self):
        from collections import defaultdict
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int | None = None, window_seconds: int = 60) -> tuple[bool, int]:
        limit = max_requests or settings.rate_limit_per_minute
        now = time.time()
        window_start = now - window_seconds
        bucket = self._buckets[key]
        bucket[:] = [ts for ts in bucket if ts > window_start]
        if len(bucket) >= limit:
            retry_after = int(bucket[0] + window_seconds - now) if bucket else window_seconds
            return False, max(1, retry_after)
        bucket.append(now)
        return True, 0


rate_limiter = RedisRateLimiter()
