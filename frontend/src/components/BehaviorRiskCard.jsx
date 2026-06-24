export function BehaviorRiskCard({ score, level, reasons, eventCount, breakdown }) {
  return (
    <article>
      <h3>Behavior Risk</h3>
      <p className="score-value">{score}/100</p>
      <p><strong>Level:</strong> {level || "low"}</p>
      <p><strong>Events observed:</strong> {eventCount || 0}</p>
      <p className="hint">This score is derived from recent clicks, key presses, route changes and visibility changes.</p>
      <div className="issue-list">
        {reasons?.map((reason) => (
          <div key={reason} className="issue-item">
            <p>{reason}</p>
          </div>
        ))}
        {!reasons?.length && <p className="hint">No behavioral signals yet.</p>}
      </div>
      <div className="behavior-breakdown">
        {Object.entries(breakdown || {}).map(([key, value]) => (
          <span key={key} className="behavior-chip">
            {key}: {value}
          </span>
        ))}
      </div>
    </article>
  );
}
