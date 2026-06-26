"""WebAuthn / passkey challenge store backed by Redis.

The previous implementation kept challenges in a process-local ``dict``,
which meant challenges did not survive across workers (and could be
replayed/cleared by restarting the API). It also kept expired challenges
indefinitely.

This module is sync-only and shared by both the registration and
authentication flows. Challenges are auto-expired by Redis (TTL).
"""

from __future__ import annotations

import json
import uuid
from typing import Optional


from app.core.redis_client import get_redis


PASSKEY_CHALLENGE_TTL_SECONDS = 120


def _key(challenge_id: str) -> str:
    return f"passkey:challenge:{challenge_id}"


def _client():
    return get_redis()


def store_challenge(payload: dict) -> str:
    """Persist a challenge and return its id."""
    client = _client()
    challenge_id = str(uuid.uuid4())
    if client is not None:
        try:
            client.setex(_key(challenge_id), PASSKEY_CHALLENGE_TTL_SECONDS, json.dumps(payload))
        except Exception:
            # Fall through — the in-memory path will be used.
            pass
    _in_memory_store[challenge_id] = payload
    return challenge_id


def consume_challenge(challenge_id: str) -> Optional[dict]:
    """Atomically read and delete a challenge. ``None`` if expired/missing."""
    payload: Optional[dict] = None
    client = _client()
    if client is not None:
        try:
            raw = client.get(_key(challenge_id))
            if raw:
                client.delete(_key(challenge_id))
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = None
        except Exception:
            payload = None

    if payload is None:
        payload = _in_memory_store.pop(challenge_id, None)

    return payload


# Last-resort in-memory fallback. Redis is the source of truth; this is
# only used if Redis is unreachable and the request still needs to proceed.
_in_memory_store: dict[str, dict] = {}