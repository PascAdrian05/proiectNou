import json
import os
from groq import Groq
from app.core.config import settings


class AIService:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None

    def is_available(self) -> bool:
        return self.client is not None

    async def analyze_finding(self, finding: dict, context: dict | None = None) -> dict:
        if not self.is_available():
            return {
                "available": False,
                "message": "AI assistant is not configured. Please add GROQ_API_KEY to enable smart insights.",
            }

        prompt = self._build_finding_prompt(finding, context)

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a cybersecurity expert assistant. "
                            "Provide clear, actionable advice about security findings. "
                            "Be concise but thorough. Always include a confidence level (high/medium/low). "
                            "Format your response as JSON with keys: summary, severity_assessment, recommendation, confidence, references."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            result["available"] = True
            return result

        except Exception as exc:
            return {
                "available": False,
                "message": f"AI analysis failed: {str(exc)}",
            }

    async def get_security_tips(self, websites: list[dict], findings: list[dict]) -> dict:
        if not self.is_available():
            return {
                "available": False,
                "message": "AI assistant is not configured.",
            }

        prompt = (
            "Based on the following security monitoring data, provide 3-5 prioritized, actionable security tips. "
            "Consider the websites monitored and the findings detected. "
            "Format as JSON with keys: tips (array of objects with priority, title, description, effort), overall_health_score (0-100)."
            f"\n\nWebsites: {[w.get('domain') for w in websites]}"
            f"\nFindings summary: {len(findings)} total findings"
        )

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful cybersecurity advisor. "
                            "Provide practical, prioritized security recommendations. "
                            "Be encouraging but honest about risks. "
                            "Format response as JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            result["available"] = True
            return result

        except Exception as exc:
            return {
                "available": False,
                "message": f"Could not generate tips: {str(exc)}",
            }

    async def verify_security_posture(self, websites: list[dict], findings: list[dict]) -> dict:
        if not self.is_available():
            return {
                "available": False,
                "message": "AI assistant is not configured.",
            }

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

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a security posture verification expert. "
                            "Provide honest assessments with clear confidence levels. "
                            "Be transparent about limitations of automated scanning. "
                            "Format response as JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            result["available"] = True
            return result

        except Exception as exc:
            return {
                "available": False,
                "message": f"Verification failed: {str(exc)}",
            }

    async def get_proactive_insights(self, websites: list[dict], findings: list[dict]) -> dict:
        """Generate proactive AI insights and recommendations."""
        if not self.is_available():
            return {
                "available": False,
                "message": "AI assistant is not configured.",
            }

        critical = [f for f in findings if str(f.get("severity", "")).lower() == "critical"]
        high = [f for f in findings if str(f.get("severity", "")).lower() == "high"]
        
        # Group findings by type
        findings_by_type = {}
        for f in findings:
            kind = f.get("kind", "unknown")
            if kind not in findings_by_type:
                findings_by_type[kind] = []
            findings_by_type[kind].append(f)

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

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a proactive security advisor. "
                            "Anticipate potential issues and provide forward-thinking recommendations. "
                            "Be specific about actions and prioritize by impact vs effort. "
                            "Format response as JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=1536,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            result["available"] = True
            result["generated_at"] = "now"
            return result

        except Exception as exc:
            return {
                "available": False,
                "message": f"Could not generate proactive insights: {str(exc)}",
            }

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

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
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
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1536,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            result["available"] = True
            result["finding_id"] = str(finding.get("id", ""))
            return result

        except Exception as exc:
            return {
                "available": False,
                "message": f"Auto-fix generation failed: {str(exc)}",
            }

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
            "Generate the most appropriate fix with exact commands or config."
        )

    def _build_finding_prompt(self, finding: dict, context: dict | None = None) -> str:
        parts = [
            "Analyze this security finding:",
            f"Title: {finding.get('title', 'N/A')}",
            f"Severity: {finding.get('severity', 'N/A')}",
            f"Type: {finding.get('kind', 'N/A')}",
            f"Details: {finding.get('details_json', 'N/A')}",
        ]

        if context:
            if context.get("website"):
                parts.append(f"Website: {context['website']}")

        return "\n".join(parts)


ai_service = AIService()