"""Behavior-risk event storage backed by the shared Redis client.

The previous implementation used a module-level Redis client created at
import time, which crashed the process if Redis was unavailable.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.redis_client import get_redis


BEHAVIOR_WINDOW_SECONDS = 300
BEHAVIOR_HISTORY_SECONDS = 3600


def _events_key(tenant_id: str, user_id: str) -> str:
    return f"behavior:events:{tenant_id}:{user_id}"


def _client():
    return get_redis()


def record_behavior_events(tenant_id: str, user_id: str, events: list[dict[str, Any]]) -> bool:
    client = _client()
    if client is None or not events:
        return False
    key = _events_key(tenant_id, user_id)
    now = datetime.now(timezone.utc)

    pipe = client.pipeline()
    for event in events:
        payload = {
            "type": str(event.get("type") or "unknown"),
            "path": str(event.get("path") or ""),
            "timestamp": event.get("timestamp") or now.isoformat(),
            "meta": event.get("meta") or {},
        }
        pipe.rpush(key, json.dumps(payload))
    pipe.expire(key, BEHAVIOR_HISTORY_SECONDS)
    try:
        pipe.execute()
        return True
    except Exception:
        return False


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def get_behavior_events(tenant_id: str, user_id: str, window_seconds: int = BEHAVIOR_WINDOW_SECONDS) -> list[dict[str, Any]]:
    client = _client()
    if client is None:
        return []
    key = _events_key(tenant_id, user_id)
    try:
        raw_events = client.lrange(key, 0, -1)
    except Exception:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    events: list[dict[str, Any]] = []

    for raw_event in raw_events:
        try:
            event = json.loads(raw_event)
        except Exception:
            continue

        timestamp = _parse_timestamp(event.get("timestamp"))
        if timestamp and timestamp >= cutoff:
            event["timestamp"] = timestamp.isoformat()
            events.append(event)

    return events


def compute_behavior_score(tenant_id: str, user_id: str) -> dict[str, Any]:
    events = get_behavior_events(tenant_id, user_id)
    if not events:
        return {
            "risk_score": 0,
            "risk_level": "low",
            "reasons": ["No suspicious behavior observed"],
            "event_count": 0,
            "event_breakdown": {},
        }

    breakdown: dict[str, int] = {}
    ordered_events = sorted(events, key=lambda event: event.get("timestamp") or "")
    for event in ordered_events:
        event_type = str(event.get("type") or "unknown")
        breakdown[event_type] = breakdown.get(event_type, 0) + 1

    risk = 5
    reasons: list[str] = []

    click_count = breakdown.get("click", 0)
    keydown_count = breakdown.get("keydown", 0)
    route_change_count = breakdown.get("route_change", 0)
    submit_count = breakdown.get("submit", 0)
    visibility_hidden_count = breakdown.get("visibility_hidden", 0)

    if click_count >= 40:
        risk += 25
        reasons.append("Very high click activity")
    elif click_count >= 20:
        risk += 15
        reasons.append("Elevated click activity")

    if keydown_count >= 120:
        risk += 25
        reasons.append("Unusually high typing activity")
    elif keydown_count >= 60:
        risk += 12
        reasons.append("High keyboard activity")

    if route_change_count >= 10:
        risk += 20
        reasons.append("Rapid navigation between routes")
    elif route_change_count >= 5:
        risk += 10
        reasons.append("Frequent route switching")

    if submit_count >= 8:
        risk += 15
        reasons.append("Repeated form submissions")
    elif submit_count >= 3:
        risk += 8
        reasons.append("Multiple form submissions")

    if visibility_hidden_count >= 3:
        risk += 10
        reasons.append("Frequent tab hiding or focus loss")

    rapid_burst_count = 0
    previous_timestamp = None
    for event in ordered_events:
        timestamp = _parse_timestamp(event.get("timestamp"))
        if not timestamp:
            continue
        if previous_timestamp and (timestamp - previous_timestamp).total_seconds() <= 1.2:
            rapid_burst_count += 1
        previous_timestamp = timestamp

    if rapid_burst_count >= 12:
        risk += 20
        reasons.append("Suspicious rapid event bursts")
    elif rapid_burst_count >= 5:
        risk += 10
        reasons.append("Several rapid interactions detected")

    if not reasons:
        reasons.append("Behavior appears normal")

    risk = max(0, min(100, risk))
    risk_level = "low" if risk < 35 else "medium" if risk < 70 else "high"

    return {
        "risk_score": risk,
        "risk_level": risk_level,
        "reasons": reasons,
        "event_count": len(events),
        "event_breakdown": breakdown,
        "recent_events": ordered_events[-15:],
    }