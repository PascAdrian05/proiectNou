"""AI service backed by Groq.

The previous implementation called ``Groq.chat.completions.create`` from
``async`` methods, which blocks the event loop while waiting for the
network. This module uses :class:`AsyncGroq` and the SDK's native
``await chat.completions.create`` instead, so the FastAPI event loop can
keep serving other requests while the model is responding.
"""

from __future__ import annotations

import json
import asyncio
from typing import Any

from groq import AsyncGroq, Groq

from app.core.config import settings


# System prompts — kept as constants so they're easier to tweak and so the
# hot path (analyze/tips/etc.) stays clean.
_SYSTEM_PROMPT_FINDING = (
    "You are a cybersecurity expert assistant. "
    "Provide clear, actionable advice about security findings. "
    "Be concise but thorough. Always include a confidence level (high/medium/low). "
    "Format your response as JSON with keys: summary, severity_assessment, recommendation, confidence, references."
)

_SYSTEM_PROMPT_TIPS = (
    "You are a helpful cybersecurity advisor. "
    "Provide practical, prioritized security recommendations. "
    "Be encouraging but honest about risks. "
    "Format response as JSON."
)

_SYSTEM_PROMPT_VERIFY = (
    "You are a security posture verification expert. "
    "Provide honest assessments with clear confidence levels. "
    "Be transparent about limitations of automated scanning. "
    "Format response as JSON."
)

_SYSTEM_PROMPT_INSIGHTS = (
    "You are a proactive security advisor. "
    "Anticipate potential issues and provide forward-thinking recommendations. "
    "Be specific about actions and prioritize by impact vs effort. "
    "Format response as JSON."
)

_SYSTEM_PROMPT_AUTOFIX = (
    "You are a senior DevOps / security engineer. "
    "Generate a concrete, copy-paste-ready fix for the given security issue. "
    "Always include exact configuration or commands. "
    "Format response as JSON with keys: "
    "summary (short description), "
    "fix_type (nginx_config/apache_config/firewall_rule/dns_change/code_change/other), "
    "steps (array of step objects with title and command_or_code), "
    "risk_level (low/medium/high), "
    "estimated_effort (minutes), "
    "rollback_instructions (string)."
)


_MODEL = "llama-3.3-70b-versatile"


class AIService:
    def __init__(self) -> None:
        self._api_key = settings.groq_api_key
        self._async_client: AsyncGroq | None = None
        self._sync_client: Groq | None = None

    @property
    def async_client(self) -> AsyncGroq | None:
        if not self._api_key:
            return None
        if self._async_client is None:
            self._async_client = AsyncGroq(api_key=self._api_key)
        return self._async_client

    @property
    def sync_client(self) -> Groq | None:
        # Used by Celery tasks where there is no running event loop.
        if not self._api_key:
            return None
        if self._sync_client is None:
            self._sync_client = Groq(api_key=self._api_key)
        return self._sync_client

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def _chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Run a chat completion that returns a JSON object."""
        client = self.async_client
        if client is None:
            return {
                "available": False,
                "message": "AI assistant is not configured. Please add GROQ_API_KEY to enable smart insights.",
            }

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
            return {"available": False, "message": f"AI request failed: {exc}"}

        try:
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
        except (json.JSONDecodeError, IndexError, AttributeError) as exc:
            return {"available": False, "message": f"AI returned invalid JSON: {exc}"}

        result["available"] = True
        return result

    def _chat_json_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Synchronous variant for Celery tasks (no running event loop)."""
        client = self.sync_client
        if client is None:
            return {
                "available": False,
                "message": "AI assistant is not configured. Please add GROQ_API_KEY to enable smart insights.",
            }

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
            return {"available": False, "message": f"AI request failed: {exc}"}

        try:
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
        except (json.JSONDecodeError, IndexError, AttributeError) as exc:
            return {"available": False, "message": f"AI returned invalid JSON: {exc}"}

        result["available"] = True
        return result

    async def analyze_finding(self, finding: dict, context: dict | None = None) -> dict:
        prompt = self._build_finding_prompt(finding, context)
        return await self._chat_json(
            _SYSTEM_PROMPT_FINDING, prompt, temperature=0.3, max_tokens=1024
        )

    async def get_security_tips(self, websites: list[dict], findings: list[dict]) -> dict:
        prompt = (
            "Based on the following security monitoring data, provide 3-5 prioritized, actionable security tips. "
            "Consider the websites monitored and the findings detected. "
            "Format as JSON with keys: tips (array of objects with priority, title, description, effort), overall_health_score (0-100)."
            f"\n\nWebsites: {[w.get('domain') for w in websites]}"
            f"\nFindings summary: {len(findings)} total findings"
        )
        return await self._chat_json(_SYSTEM_PROMPT_TIPS, prompt, temperature=0.4, max_tokens=1024)

    async def verify_security_posture(self, websites: list[dict], findings: list[dict]) -> dict:
        critical = [f for f in findings if str(f.get("severity", "")).lower() == "critical"]
        high = [f for f in findings if str(f.get("severity", "")).lower() == "high"]

        prompt = (
            "Perform a security posture verification for this monitoring setup. "
            "Assess the overall security health and provide a verification summary. "
            "Format as JSON with keys: posture_score (0-100), status (healthy/needs_attention/critical), "
            "verification_summary, immediate_actions (array), long_term_recommendations (array)."
            f"\n\nMonitored websites: {len(websites)}"
            f"\nCritical findings: {len(critical)}"
            f"\nHigh findings: {len(high)}"
            f"\nTotal findings: {len(findings)}"
        )
        return await self._chat_json(_SYSTEM_PROMPT_VERIFY, prompt, temperature=0.3, max_tokens=1024)

    async def get_proactive_insights(self, websites: list[dict], findings: list[dict]) -> dict:
        critical = [f for f in findings if str(f.get("severity", "")).lower() == "critical"]
        high = [f for f in findings if str(f.get("severity", "")).lower() == "high"]

        findings_by_type: dict[str, list] = {}
        for f in findings:
            kind = f.get("kind", "unknown")
            findings_by_type.setdefault(kind, []).append(f)

        prompt = (
            "Analyze the current security posture and provide proactive, actionable insights. "
            "Focus on: 1) Immediate security risks to address, 2) Quick wins for improvement, "
            "3) Long-term security strategy recommendations. "
            "Format as JSON with keys: immediate_risks (array with title, severity, action), "
            "quick_wins (array with title, benefit, effort), strategic_recommendations (array), "
            "trend_analysis (string describing security trend), priority_order (array of finding types to address first)."
            f"\n\nWebsites monitored: {len(websites)}"
            f"\nCritical findings: {len(critical)}"
            f"\nHigh findings: {len(high)}"
            f"\nTotal open findings: {len(findings)}"
            f"\nFinding types: {list(findings_by_type.keys())}"
        )
        result = await self._chat_json(
            _SYSTEM_PROMPT_INSIGHTS, prompt, temperature=0.4, max_tokens=1536
        )
        if result.get("available"):
            result["generated_at"] = "now"
        return result

    async def auto_fix_finding(self, finding: dict, context: dict | None = None) -> dict:
        if not self.is_available():
            return {
                "available": False,
                "message": "AI auto-fix is not configured. Please add GROQ_API_KEY.",
            }

        kind = finding.get("kind", "unknown")
        details = finding.get("details_json", "{}")
        website = (context or {}).get("website", "your-site.com")

        try:
            details_parsed = json.loads(details) if isinstance(details, str) else details
        except (json.JSONDecodeError, TypeError):
            details_parsed = {}

        prompt = self._build_autofix_prompt(kind, details_parsed, website)
        result = await self._chat_json(
            _SYSTEM_PROMPT_AUTOFIX, prompt, temperature=0.2, max_tokens=1536
        )
        if result.get("available"):
            result["finding_id"] = str(finding.get("id", ""))
        return result

    # --- sync variants for Celery -----------------------------------------

    def analyze_finding_sync(self, finding: dict, context: dict | None = None) -> dict:
        return self._chat_json_sync(
            _SYSTEM_PROMPT_FINDING,
            self._build_finding_prompt(finding, context),
            temperature=0.3,
            max_tokens=1024,
        )

    def get_security_tips_sync(self, websites: list[dict], findings: list[dict]) -> dict:
        prompt = (
            "Based on the following security monitoring data, provide 3-5 prioritized, actionable security tips. "
            "Consider the websites monitored and the findings detected. "
            "Format as JSON with keys: tips (array of objects with priority, title, description, effort), overall_health_score (0-100)."
            f"\n\nWebsites: {[w.get('domain') for w in websites]}"
            f"\nFindings summary: {len(findings)} total findings"
        )
        return self._chat_json_sync(_SYSTEM_PROMPT_TIPS, prompt, temperature=0.4, max_tokens=1024)

    def auto_fix_finding_sync(self, finding: dict, context: dict | None = None) -> dict:
        kind = finding.get("kind", "unknown")
        details = finding.get("details_json", "{}")
        website = (context or {}).get("website", "your-site.com")
        try:
            details_parsed = json.loads(details) if isinstance(details, str) else details
        except (json.JSONDecodeError, TypeError):
            details_parsed = {}
        result = self._chat_json_sync(
            _SYSTEM_PROMPT_AUTOFIX,
            self._build_autofix_prompt(kind, details_parsed, website),
            temperature=0.2,
            max_tokens=1536,
        )
        if result.get("available"):
            result["finding_id"] = str(finding.get("id", ""))
        return result

    def _build_autofix_prompt(self, kind: str, details: dict, website: str) -> str:
        prompts = {
            "uptime": (
                f"Website {website} is unreachable. Details: {json.dumps(details)}. "
                "Generate a fix. If server is down, provide restart/healthcheck commands. "
                "If DNS issue, provide DNS check + fix commands. "
                "Include curl test command to verify the fix."
            ),
            "ssl_expiry": (
                f"SSL certificate for {website} has issues. Details: {json.dumps(details)}. "
                "Generate fix commands. Include: certbot renew / nginx reload commands, "
                "or manual certificate renewal steps. "
                "Include verification with openssl."
            ),
            "security_headers": (
                f"Security headers missing on {website}. Details: {json.dumps(details)}. "
                "Generate exact Nginx or Apache config snippet to add: "
                "Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options, "
                "Content-Security-Policy, Referrer-Policy. "
                "Include curl test to verify headers after fix."
            ),
            "open_ports": (
                f"Unnecessary open ports detected on {website}. Details: {json.dumps(details)}. "
                "Generate iptables/ufw firewall rules to close those ports. "
                "Include verification with nmap or netstat."
            ),
        }
        return prompts.get(
            kind,
            f"Security finding type '{kind}' on {website}. Details: {json.dumps(details)}. "
            "Generate the most appropriate fix with exact commands or config.",
        )

    def _build_finding_prompt(self, finding: dict, context: dict | None = None) -> str:
        parts = [
            "Analyze this security finding:",
            f"Title: {finding.get('title', 'N/A')}",
            f"Severity: {finding.get('severity', 'N/A')}",
            f"Type: {finding.get('kind', 'N/A')}",
            f"Details: {finding.get('details_json', 'N/A')}",
        ]
        if context and context.get("website"):
            parts.append(f"Website: {context['website']}")
        return "\n".join(parts)


ai_service = AIService()