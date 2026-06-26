import { useState } from "react";
import { enrichFinding } from "../utils/findingLabels";
import { SeverityBadge } from "./SeverityBadge";
import { AiAutoFixPanel } from "./AiAutoFixPanel";

export function FindingCard({ finding, websiteDomain, showSteps = true, compact = false, onResolved }) {
  const enriched = enrichFinding(finding);
  const [showFix, setShowFix] = useState(false);
  const [resolved, setResolved] = useState(false);

  if (resolved) {
    return (
      <article className={`finding-card finding-resolved${compact ? " finding-card-compact" : ""}`}>
        <div className="finding-header">
          <h4><span style={{ color: "var(--accent-2)" }}>{"\u2705"}</span> {enriched.humanTitle}</h4>
          <SeverityBadge severity={finding.severity} />
        </div>
        <p style={{ color: "var(--accent-2)", fontWeight: 600 }}>Resolved by AI Auto-Fix</p>
      </article>
    );
  }

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

      <div className="finding-actions">
        <button
          type="button"
          className="ai-autofix-btn"
          onClick={() => setShowFix(!showFix)}
        >
          {showFix ? "Hide fix" : "AI Auto-Fix"}
        </button>
      </div>

      {showFix && (
        <AiAutoFixPanel
          findingId={finding.id}
          finding={finding}
          onClose={() => setShowFix(false)}
          onResolved={() => {
            setResolved(true);
            setShowFix(false);
            if (onResolved) onResolved(finding.id);
          }}
        />
      )}
    </article>
  );
}
