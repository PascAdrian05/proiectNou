import { useEffect, useState } from "react";
import { alertsService } from "../services/api/alertsService";
import { createEventSource } from "../services/api/eventStream";
import { useAuth } from "../context/AuthContext";
import { appConfig } from "../config/appConfig";

function formatTimestamp(value) {
  if (!value) {
    return "n/a";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

export function AlertsPage() {
  const { isAuthenticated } = useAuth();
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  async function loadAlerts() {
    setError("");
    setIsBusy(true);
    try {
      const data = await alertsService.list();
      setAlerts(data);
    } catch (loadError) {
      setError(loadError.message || "Could not load alerts");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    loadAlerts();
  }, []);

  useEffect(() => {
    const session = localStorage.getItem("authSession");
    const parsedSession = session ? JSON.parse(session) : null;
    const source = createEventSource(`/api/v1/events/alerts/stream`, {
      session: parsedSession,
    });

    source.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload?.alerts) {
        setAlerts((current) => {
          const updated = new Map(current.map((alert) => [alert.id, alert]));
          for (const remote of payload.alerts) {
            updated.set(remote.id, { ...updated.get(remote.id), ...remote });
          }
          return Array.from(updated.values());
        });
      }
    };

    source.onerror = () => {
      source.close();
    };

    return () => {
      source.close();
    };
  }, []);

  async function deleteAlert(alertId) {
    const confirmed = window.confirm("Delete this alert?");
    if (!confirmed) {
      return;
    }

    setError("");
    setIsBusy(true);
    try {
      await alertsService.remove(alertId);
      await loadAlerts();
    } catch (deleteError) {
      setError(deleteError.message || "Could not delete alert");
      setIsBusy(false);
    }
  }

  return (
    <section className="page-card">
      <div className="list-header">
        <h2>Alerts</h2>
        <button type="button" onClick={loadAlerts} disabled={isBusy || !isAuthenticated}>Refresh</button>
      </div>
      <p className="hint">Delivered alerts and delivery statuses.</p>
      {error && <p className="error-text">{error}</p>}

      <div className="list-grid">
        {alerts.map((alert) => (
          <article key={alert.id}>
            <h4>{alert.channel || "unknown"}</h4>
            <p><strong>Recipient:</strong> {alert.recipient || "n/a"}</p>
            <p><strong>Status:</strong> {alert.status || "pending"}</p>
            <p><strong>Sent:</strong> {formatTimestamp(alert.sent_at || alert.created_at)}</p>
            <div className="card-actions">
              <button type="button" className="danger-button" onClick={() => deleteAlert(alert.id)} disabled={isBusy || !isAuthenticated}>
                Delete alert
              </button>
            </div>
          </article>
        ))}
        {!alerts.length && !isBusy && <p className="hint">No alerts yet.</p>}
      </div>
    </section>
  );
}
