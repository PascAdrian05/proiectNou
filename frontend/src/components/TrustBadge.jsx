import { useEffect, useState } from "react";

export function TrustBadge() {
  const [stats, setStats] = useState({ total_websites: 0, active_websites: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTrustStats() {
      try {
        const response = await fetch("/api/v1/trust/stats");
        const data = await response.json();
        setStats(data);
      } catch (error) {
        console.error("Failed to fetch trust stats:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchTrustStats();
    // Refresh every 5 minutes
    const interval = setInterval(fetchTrustStats, 300000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="trust-badge">
        <span className="trust-icon">🛡️</span>
        <span className="trust-text">Loading...</span>
      </div>
    );
  }

  return (
    <div className="trust-badge">
      <span className="trust-icon">🛡️</span>
      <span className="trust-text">
        {stats.total_websites.toLocaleString()} sites monitored
      </span>
    </div>
  );
}
