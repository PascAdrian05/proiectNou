import { enrichFinding } from "../utils/findingLabels";
import { SeverityBadge } from "./SeverityBadge";

export function FindingCard({ finding, websiteDomain, showSteps = true, compact = false }) {
  const enriched = enrichFinding(finding);

  return (
    <article className={`finding-card${compact ? " finding-card-compact" : ""}`}>
      <div className="finding-header">
        <h4>{enriched.humanTitle}</h4>
        <SeverityBadge severity={finding.severity} />
      </div>
      {websiteDomain && <p className="hint finding-domain">{websiteDomain}</p>}
      <p>{enriched.humanSummary}</p>
      {showSteps && (
        <div className="remediation-steps">
          <p className="remediation-label">What to do:</p>
          <ol>
            {enriched.remediationSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
      )}
    </article>
  );
}
