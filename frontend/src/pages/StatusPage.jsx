import { useEffect, useState } from "react";

export function StatusPage() {
  const [statusData, setStatusData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const response = await fetch("/api/v1/status/public");
        const data = await response.json();
        setStatusData(data);
        setLastUpdated(new Date());
      } catch (error) {
        console.error("Failed to fetch status:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchStatus();
    // Refresh every 60 seconds
    const interval = setInterval(fetchStatus, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <section className="page-card">
        <div className="list-header">
          <h2>System Status</h2>
        </div>
        <p className="route-loader">Loading status...</p>
      </section>
    );
  }

  const overallStatus = statusData?.status || "unknown";
  const isOperational = overallStatus === "operational";

  return (
    <section className="page-card">
      <div className="list-header">
        <h2>System Status</h2>
        <p className="hint">
          {lastUpdated ? `Last updated: ${lastUpdated.toLocaleTimeString()}` : ""}
        </p>
      </div>

      <div className="status-overview">
        <div className={`status-banner ${isOperational ? "operational" : "degraded"}`}>
          <span className="status-icon">{isOperational ? "✅" : "⚠️"}</span>
          <div>
            <h3>{isOperational ? "All Systems Operational" : "System Degraded"}</h3>
            <p className="hint">
              {isOperational
                ? "All services are running normally"
                : "Some services may be experiencing issues"}
            </p>
          </div>
        </div>
      </div>

      <div className="status-services">
        <h3>Services</h3>
        <div className="service-grid">
          {statusData?.services &&
            Object.entries(statusData.services).map(([serviceName, serviceData]) => (
              <div key={serviceName} className="service-card">
                <div className="service-header">
                  <h4>{serviceName.charAt(0).toUpperCase() + serviceName.slice(1)}</h4>
                  <span
                    className={`service-status ${
                      serviceData.status === "operational" ? "operational" : "degraded"
                    }`}
                  >
                    {serviceData.status === "operational" ? "●" : "●"} {serviceData.status}
                  </span>
                </div>
                <p className="hint">Uptime: {serviceData.uptime || "N/A"}</p>
              </div>
            ))}
        </div>
      </div>

      {statusData?.incidents && statusData.incidents.length > 0 && (
        <div className="status-incidents">
          <h3>Active Incidents</h3>
          <div className="incident-list">
            {statusData.incidents.map((incident, index) => (
              <div key={index} className="incident-card">
                <h4>{incident.title || "Incident"}</h4>
                <p className="hint">{incident.description || "No description available"}</p>
                <p className="hint">Started: {incident.started_at || "Unknown"}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {!isOperational && (
        <div className="status-message">
          <p>
            We are actively working to resolve the issue. Check back here for updates or follow our
            social media for real-time notifications.
          </p>
        </div>
      )}
    </section>
  );
}
