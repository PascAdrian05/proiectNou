export function StatCard({ label, value, hint, accent }) {
  return (
    <article className={`stat-card${accent ? ` stat-card-${accent}` : ""}`}>
      <p className="stat-label">{label}</p>
      <p className="stat-value">{value}</p>
      {hint && <p className="hint">{hint}</p>}
    </article>
  );
}
