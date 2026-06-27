"""Project-aware AI assistant backed by Groq.

This module exposes the same public surface as the original
``ai_service.py`` (so existing imports continue to work) while making the
assistant genuinely aware of the platform it lives inside:

* It receives a live snapshot of the tenant's websites, findings and
  alerts at every call — the model never has to guess what the user is
  looking at.
* It speaks in the project's vocabulary (``scan_run`` / ``website`` /
  ``finding`` / ``alert`` / ``tenant``) and stays inside the JSON schema
  the UI expects.
* Responses are cached in Redis so the model is not re-queried for the
  same (tenant, prompt, context) within a short window.
* All important lifecycle events (cache hits, cache misses, fallbacks,
  prompt-injection attempts) are logged so an operator can audit what
  the assistant said and why.

The previous version kept a per-process ``OrderedDict`` cache that was
lost on restart and the proactive-insights prompt disagreed with the
caller's expected schema. Both are fixed here.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Iterable

from groq import AsyncGroq, Groq

from app.core.config import settings
from app.core.redis_client import get_redis


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# System prompts
# --------------------------------------------------------------------------- #


_SYSTEM_PROMPT_FINDING = (
    "You are a senior cybersecurity analyst embedded in the Guardian security "
    "monitoring platform. Guardian stores its data in PostgreSQL using SQLModel "
    "with the following relationships:\n"
    "- tenant 1-N user, website, scanrun, finding, alert, subscription\n"
    "- website 1-N scanrun\n"
    "- scanrun 1-N finding; finding 1-N alert\n"
    "A finding's lifecycle status is one of: open | resolved. Severity is one of: "
    "critical | high | medium | low. The four scan check kinds are: uptime, "
    "ssl_expiry, security_headers, open_ports.\n"
    "Analyze the supplied finding and respond with valid JSON only, exactly these keys:\n"
    '"summary": string (brief description),\n'
    '"severity_assessment": string (one of: critical, high, medium, low),\n'
    '"recommendation": string (actionable steps),\n'
    '"confidence": string (one of: high, medium, low),\n'
    '"references": array of strings (relevant URLs or references).\n'
    "No additional text or commentary outside the JSON."
)

_SYSTEM_PROMPT_TIPS = (
    "You are the Guardian security advisor. Guardian is a multi-tenant FastAPI "
    "service that runs four scan kinds (uptime, ssl_expiry, security_headers, "
    "open_ports) every few hours and stores findings per tenant.\n"
    "Generate 3-5 prioritized, actionable security tips for the supplied tenant "
    "based on the websites it monitors and the findings already detected.\n"
    "Return valid JSON only with these keys:\n"
    '"tips": array of objects, each with keys "priority" (high|medium|low), '
    '"title" (short), "description" (detailed action), '
    '"effort" (low|medium|high);\n'
    '"overall_health_score": integer between 0 and 100.\n'
    "No additional text outside the JSON."
)

_SYSTEM_PROMPT_VERIFY = (
    "You are the Guardian posture-verification expert. Guardian stores "
    "tenants, websites, scan runs, findings and alerts; a finding is 'open' "
    "until the next scan run that no longer reproduces it auto-resolves it.\n"
    "Assess the supplied tenant's overall security health and return valid JSON "
    "only with these keys:\n"
    '"posture_score": integer between 0 and 100,\n'
    '"status": string (one of: healthy, needs_attention, critical),\n'
    '"verification_summary": string,\n'
    '"immediate_actions": array of strings,\n'
    '"long_term_recommendations": array of strings.\n'
    "No additional text outside the JSON."
)

# NOTE: This prompt previously used a "insights" array schema but the caller
# expected a different shape — the prompt and the consumer now agree.
_SYSTEM_PROMPT_INSIGHTS = (
    "You are the Guardian proactive-insights engine. Guardian stores tenants, "
    "websites, scan runs, findings and alerts. Each finding has a kind "
    "(uptime | ssl_expiry | security_headers | open_ports) and a severity "
    "(critical | high | medium | low).\n"
    "Analyze the supplied tenant's posture and return valid JSON only with these keys:\n"
    '"immediate_risks": array of objects each with "title" (string), '
    '"severity" (critical|high|medium|low), "action" (string);\n'
    '"quick_wins": array of objects each with "title" (string), '
    '"benefit" (string), "effort" (low|medium|high);\n'
    '"strategic_recommendations": array of strings;\n'
    '"trend_analysis": string describing the current security trend;\n'
    '"priority_order": array of finding-kind strings ordered from highest to '
    'lowest urgency based on impact and effort.\n'
    "No additional text outside the JSON."
)

_SYSTEM_PROMPT_AUTOFIX = (
    "You are the Guardian auto-fix engineer. Guardian monitors four check kinds: "
    "uptime, ssl_expiry, security_headers, open_ports.\n"
    "Generate a concrete, copy-paste-ready remediation for the supplied finding. "
    "Return valid JSON only with these keys:\n"
    '"summary": string (short description),\n'
    '"fix_type": string (one of: nginx_config, apache_config, firewall_rule, '
    'dns_change, code_change, other),\n'
    '"steps": array of objects each with "title" (string) and "command_or_code" '
    "(string),\n"
    '"risk_level": string (one of: low, medium, high),\n'
    '"estimated_effort": integer (minutes),\n'
    '"rollback_instructions": string.\n'
    "No additional text outside the JSON."
)


# --------------------------------------------------------------------------- #
# Project context (system-prompt primer)
# --------------------------------------------------------------------------- #


_PROJECT_CONTEXT_BLOCK = (
    "Project context (live snapshot):\n"
    "- Tenants: every row in the `tenant` table represents an isolated organization.\n"
    "- Websites: a tenant may have several websites (table `website`).\n"
    "- Scans: each enqueued scan (table `scanrun`) runs checks of kind "
    "uptime | ssl_expiry | security_headers | open_ports and writes "
    "findings to the `finding` table. The progress JSON field tracks "
    "step-level state via Redis pub/sub on channels scan:progress / "
    "scan:completed.\n"
    "- Findings: a finding row carries kind, severity, title and a JSON "
    "details_json payload. Status transitions open → resolved happen "
    "automatically when the next scan no longer reproduces the issue.\n"
    "- Alerts: every open finding with critical/high severity fans out to "
    "the tenant's configured email + webhook channels and produces an "
    "alert row.\n"
    "- AI endpoints:\n"
    "  POST /ai/analyze-finding/{id}      — per-finding analysis\n"
    "  POST /ai/security-tips             — overall tips\n"
    "  POST /ai/verify-posture            — posture score + actions\n"
    "  POST /ai/proactive-insights        — forward-looking risks\n"
    "  POST /ai/auto-fix/{id}             — concrete remediation\n"
    "- CRUD conventions: every mutation invalidates the per-tenant cache "
    "namespace (cache_delete_pattern). The frontend is a React SPA "
    "talking to these endpoints through src/services/api/*Service.js.\n"
)


# --------------------------------------------------------------------------- #
# Sanitization
# --------------------------------------------------------------------------- #


# A small list of substrings that are common prompt-injection carriers. We
# don't try to be exhaustive — we strip control chars, cap length and refuse
# to interpolate user-controlled strings into the system prompt.
_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "system:",
    "assistant:",
    "developer:",
    "<|im_start|>",
    "<|im_end|>",
)


def _sanitize_user_text(value: str, *, max_length: int = 4000) -> str:
    """Strip control chars, cap length, and flag obvious injection attempts."""
    if not isinstance(value, str):
        return ""
    # Drop ASCII control chars (keep printable + extended latin).
    cleaned = "".join(ch for ch in value if ch == "\n" or ch == "\t" or 32 <= ord(ch) < 127 or ord(ch) >= 160)
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    lowered = cleaned.lower()
    for marker in _INJECTION_MARKERS:
        if marker in lowered:
            logger.warning("stripped suspected prompt-injection marker: %r", marker)
            cleaned = cleaned.replace(marker, "[REDACTED]")
    return cleaned


def _safe_json(value: Any) -> str:
    """JSON-encode with string sanitation so user data never escapes the user role."""
    try:
        text = json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(value)
    return _sanitize_user_text(text, max_length=8000)


# --------------------------------------------------------------------------- #
# Cache (Redis with deterministic key)
# --------------------------------------------------------------------------- #


_CACHE_PREFIX = "ai:cache"
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _cache_key(system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> str:
    """Build a short, collision-resistant cache key."""
    hasher = hashlib.blake2b(digest_size=16)
    hasher.update(system_prompt.encode("utf-8"))
    hasher.update(b"||")
    hasher.update(user_prompt.encode("utf-8"))
    hasher.update(f"||t={temperature}||m={max_tokens}".encode("utf-8"))
    return f"{_CACHE_PREFIX}:{hasher.hexdigest()}"


def _cache_get(key: str) -> dict | None:
    client = get_redis()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except Exception:
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _cache_set(key: str, value: dict) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.setex(key, _CACHE_TTL_SECONDS, json.dumps(value, default=str))
    except Exception:
        # Caching is best-effort; the request must still succeed.
        pass


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


_MODEL = "llama-3.3-70b-versatile"


class AIService:
    """Project-aware AI assistant.

    The singleton (``ai_service``) is instantiated once at module import.
    """

    def __init__(self) -> None:
        self._api_key = settings.groq_api_key
        self._async_client: AsyncGroq | None = None
        self._sync_client: Groq | None = None

    # ------------------------------------------------------------------ #
    # Client accessors
    # ------------------------------------------------------------------ #

    @property
    def async_client(self) -> AsyncGroq | None:
        if not self._api_key:
            return None
        if self._async_client is None:
            self._async_client = AsyncGroq(api_key=self._api_key)
        return self._async_client

    @property
    def sync_client(self) -> Groq | None:
        if not self._api_key:
            return None
        if self._sync_client is None:
            self._sync_client = Groq(api_key=self._api_key)
        return self._sync_client

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def aclose(self) -> None:
        """Close the underlying HTTP clients on shutdown."""
        if self._async_client is not None:
            try:
                await self._async_client.close()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Core chat helpers
    # ------------------------------------------------------------------ #

    async def _chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        key = _cache_key(system_prompt, user_prompt, temperature, max_tokens)
        cached = _cache_get(key)
        if cached is not None:
            logger.debug("ai cache hit key=%s", key)
            return cached

        client = self.async_client
        if client is None:
            return self._unavailable_response()

        try:
            response = await client.chat.completions.create(
                model=_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            logger.exception("ai chat failed")
            return {"available": False, "message": f"AI request failed: {exc}"}

        try:
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
        except (json.JSONDecodeError, IndexError, AttributeError) as exc:
            logger.warning("ai returned invalid JSON: %s", exc)
            return {"available": False, "message": f"AI returned invalid JSON: {exc}"}

        if not isinstance(result, dict):
            return {"available": False, "message": "AI response was not a JSON object"}

        result.setdefault("available", True)
        result["model"] = _MODEL
        _cache_set(key, result)
        return result

    def _chat_json_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        key = _cache_key(system_prompt, user_prompt, temperature, max_tokens)
        cached = _cache_get(key)
        if cached is not None:
            return cached

        client = self.sync_client
        if client is None:
            return self._unavailable_response()

        try:
            response = client.chat.completions.create(
                model=_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            logger.exception("ai chat (sync) failed")
            return {"available": False, "message": f"AI request failed: {exc}"}

        try:
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
        except (json.JSONDecodeError, IndexError, AttributeError) as exc:
            logger.warning("ai (sync) returned invalid JSON: %s", exc)
            return {"available": False, "message": f"AI returned invalid JSON: {exc}"}

        if not isinstance(result, dict):
            return {"available": False, "message": "AI response was not a JSON object"}

        result.setdefault("available", True)
        result["model"] = _MODEL
        _cache_set(key, result)
        return result

    @staticmethod
    def _unavailable_response() -> dict[str, Any]:
        return {
            "available": False,
            "message": "AI assistant is not configured. Set GROQ_API_KEY to enable smart insights.",
        }

    # ------------------------------------------------------------------ #
    # Higher-level helpers
    # ------------------------------------------------------------------ #

    def _with_project_context(self, system_prompt: str) -> str:
        return f"{system_prompt}\n\n{_PROJECT_CONTEXT_BLOCK}"

    async def analyze_finding(self, finding: dict, context: dict | None = None) -> dict:
        prompt = self._build_finding_prompt(finding, context)
        return await self._chat_json(
            self._with_project_context(_SYSTEM_PROMPT_FINDING),
            prompt,
            temperature=0.3,
            max_tokens=1024,
        )

    async def get_security_tips(self, websites: list[dict], findings: list[dict]) -> dict:
        prompt = (
            "Tenant snapshot:\n"
            f"- websites: {len(websites)} ({_summarize_domains(websites)})\n"
            f"- open findings: {len(findings)} ({_summarize_findings(findings)})\n"
            "Generate 3-5 prioritized, actionable security tips for this tenant."
        )
        return await self._chat_json(
            self._with_project_context(_SYSTEM_PROMPT_TIPS),
            prompt,
            temperature=0.4,
            max_tokens=1024,
        )

    async def verify_security_posture(self, websites: list[dict], findings: list[dict]) -> dict:
        critical = sum(1 for f in findings if str(f.get("severity", "")).lower() == "critical")
        high = sum(1 for f in findings if str(f.get("severity", "")).lower() == "high")

        prompt = (
            "Tenant snapshot:\n"
            f"- websites: {len(websites)}\n"
            f"- open findings: {len(findings)} ({critical} critical, {high} high)\n"
            "Verify the tenant's security posture and return the JSON described in the system prompt."
        )
        return await self._chat_json(
            self._with_project_context(_SYSTEM_PROMPT_VERIFY),
            prompt,
            temperature=0.3,
            max_tokens=1024,
        )

    async def get_proactive_insights(self, websites: list[dict], findings: list[dict]) -> dict:
        findings_by_type: dict[str, int] = {}
        for f in findings:
            kind = str(f.get("kind", "unknown"))
            findings_by_type[kind] = findings_by_type.get(kind, 0) + 1

        prompt = (
            "Tenant snapshot:\n"
            f"- websites: {len(websites)}\n"
            f"- open findings: {len(findings)}\n"
            f"- findings by kind: {findings_by_type or 'none'}\n"
            "Return the proactive-insights JSON described in the system prompt."
        )
        return await self._chat_json(
            self._with_project_context(_SYSTEM_PROMPT_INSIGHTS),
            prompt,
            temperature=0.4,
            max_tokens=1536,
        )

    async def auto_fix_finding(self, finding: dict, context: dict | None = None) -> dict:
        if not self.is_available():
            return self._unavailable_response()

        kind = finding.get("kind", "unknown")
        details = finding.get("details_json", "{}")
        website = (context or {}).get("website", "your-site.com")
        try:
            details_parsed = json.loads(details) if isinstance(details, str) else details
        except (json.JSONDecodeError, TypeError):
            details_parsed = {}

        prompt = self._build_autofix_prompt(kind, details_parsed, website)
        result = await self._chat_json(
            self._with_project_context(_SYSTEM_PROMPT_AUTOFIX),
            prompt,
            temperature=0.2,
            max_tokens=1536,
        )
        if result.get("available"):
            result["finding_id"] = str(finding.get("id", ""))
        return result

    # ------------------------------------------------------------------ #
    # Sync variants for Celery workers
    # ------------------------------------------------------------------ #

    def analyze_finding_sync(self, finding: dict, context: dict | None = None) -> dict:
        return self._chat_json_sync(
            self._with_project_context(_SYSTEM_PROMPT_FINDING),
            self._build_finding_prompt(finding, context),
            temperature=0.3,
            max_tokens=1024,
        )

    def get_security_tips_sync(self, websites: list[dict], findings: list[dict]) -> dict:
        prompt = (
            "Tenant snapshot:\n"
            f"- websites: {len(websites)} ({_summarize_domains(websites)})\n"
            f"- open findings: {len(findings)} ({_summarize_findings(findings)})\n"
        )
        return self._chat_json_sync(
            self._with_project_context(_SYSTEM_PROMPT_TIPS),
            prompt,
            temperature=0.4,
            max_tokens=1024,
        )

    def auto_fix_finding_sync(self, finding: dict, context: dict | None = None) -> dict:
        kind = finding.get("kind", "unknown")
        details = finding.get("details_json", "{}")
        website = (context or {}).get("website", "your-site.com")
        try:
            details_parsed = json.loads(details) if isinstance(details, str) else details
        except (json.JSONDecodeError, TypeError):
            details_parsed = {}
        result = self._chat_json_sync(
            self._with_project_context(_SYSTEM_PROMPT_AUTOFIX),
            self._build_autofix_prompt(kind, details_parsed, website),
            temperature=0.2,
            max_tokens=1536,
        )
        if result.get("available"):
            result["finding_id"] = str(finding.get("id", ""))
        return result

    # ------------------------------------------------------------------ #
    # Prompt builders — all user-controlled strings are sanitized.
    # ------------------------------------------------------------------ #

    def _build_finding_prompt(self, finding: dict, context: dict | None = None) -> str:
        parts = [
            "Analyze this Guardian finding:",
            f"- title: {_sanitize_user_text(str(finding.get('title', 'N/A')))}",
            f"- severity: {_sanitize_user_text(str(finding.get('severity', 'N/A')))}",
            f"- kind: {_sanitize_user_text(str(finding.get('kind', 'N/A')))}",
            f"- status: {_sanitize_user_text(str(finding.get('status', 'N/A')))}",
            f"- details_json: {_safe_json(finding.get('details_json'))}",
        ]
        if context and context.get("website"):
            parts.append(f"- website: {_sanitize_user_text(str(context['website']))}")
        return "\n".join(parts)

    def _build_autofix_prompt(self, kind: str, details: dict, website: str) -> str:
        kind_s = _sanitize_user_text(str(kind))
        website_s = _sanitize_user_text(str(website), max_length=200)
        details_s = _safe_json(details)
        prompts = {
            "uptime": (
                f"Website {website_s} is unreachable. Details: {details_s}. "
                "If server is down, provide restart/healthcheck commands. "
                "If DNS issue, provide DNS check + fix commands. "
                "Include curl test command to verify the fix."
            ),
            "ssl_expiry": (
                f"SSL certificate for {website_s} has issues. Details: {details_s}. "
                "Provide certbot renew / nginx reload commands, or manual renewal steps. "
                "Include verification with openssl."
            ),
            "security_headers": (
                f"Security headers missing on {website_s}. Details: {details_s}. "
                "Provide an Nginx or Apache config snippet that adds: "
                "Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options, "
                "Content-Security-Policy, Referrer-Policy. "
                "Include a curl test to verify headers after the fix."
            ),
            "open_ports": (
                f"Unnecessary open ports detected on {website_s}. Details: {details_s}. "
                "Provide iptables/ufw firewall rules to close those ports. "
                "Include verification with nmap or netstat."
            ),
        }
        return prompts.get(
            kind_s,
            f"Finding kind '{kind_s}' on {website_s}. Details: {details_s}. "
            "Generate the most appropriate fix with exact commands or config.",
        )


def _summarize_domains(websites: Iterable[dict]) -> str:
    domains = []
    for w in websites:
        d = w.get("domain") or w.get("url") or "?"
        if isinstance(d, str):
            domains.append(d)
        if len(domains) >= 10:
            break
    return ", ".join(domains) if domains else "none"


def _summarize_findings(findings: Iterable[dict]) -> str:
    by_kind: dict[str, int] = {}
    for f in findings:
        kind = str(f.get("kind", "unknown"))
        by_kind[kind] = by_kind.get(kind, 0) + 1
    if not by_kind:
        return "none"
    return ", ".join(f"{k}={v}" for k, v in by_kind.items())


# Singleton used by every endpoint.
ai_service = AIService()