import hashlib
import hmac
import json
import time
from typing import Optional

from app.core.config import settings

COOKIE_NAME = "__Secure_trust_device"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


def _generate_fingerprint(user_agent: str, ip_prefix: str) -> str:
    """Generate a device fingerprint from request attributes."""
    raw = f"{user_agent}|{ip_prefix}"
    return hashlib.sha256(raw.encode()).hexdigest()


def create_trusted_device_token(user_id: str, fingerprint: str) -> str:
    """Create a signed trusted device token."""
    payload = {
        "uid": user_id,
        "fp": fingerprint,
        "exp": int(time.time()) + COOKIE_MAX_AGE,
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(
        settings.secret_key.encode(),
        payload_json.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_json}.{signature}"


def verify_trusted_device_token(token: str, user_id: str, fingerprint: str) -> bool:
    """Verify a trusted device token."""
    try:
        payload_json, signature = token.rsplit(".", 1)
        expected_sig = hmac.new(
            settings.secret_key.encode(),
            payload_json.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return False

        payload = json.loads(payload_json)
        if payload.get("uid") != user_id:
            return False
        if payload.get("fp") != fingerprint:
            return False
        if payload.get("exp", 0) < time.time():
            return False

        return True
    except (ValueError, json.JSONDecodeError, KeyError):
        return False


def build_device_fingerprint(request) -> str:
    """Build a device fingerprint from a FastAPI request."""
    user_agent = request.headers.get("user-agent", "unknown")
    # Use /24 IP prefix for privacy + reasonable accuracy
    client_ip = request.client.host if request.client else "unknown"
    ip_parts = client_ip.rsplit(".", 1)
    ip_prefix = ip_parts[0] if len(ip_parts) > 1 else client_ip
    return _generate_fingerprint(user_agent, ip_prefix)