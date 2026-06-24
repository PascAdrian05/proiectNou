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

            import json
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

            import json
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

            import json
            content = response.choices[0].message.content
            result = json.loads(content)
            result["available"] = True
            return result

        except Exception as exc:
            return {
                "available": False,
                "message": f"Verification failed: {str(exc)}",
            }

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