const severityClassMap = {
  critical: "severity-critical",
  high: "severity-high",
  medium: "severity-medium",
  low: "severity-low",
  info: "severity-info",
};

export function SeverityBadge({ severity }) {
  const normalized = String(severity || "info").toLowerCase();
  const className = severityClassMap[normalized] || "severity-info";

  return <span className={`severity-pill ${className}`}>{normalized}</span>;
}
