import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { appConfig } from "../config/appConfig";
import { scansService } from "../services/api/scansService";
import { websitesService } from "../services/api/websitesService";
import { createEventSource } from "../services/api/eventStream";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";

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

export function ScansPage() {
  const navigate = useNavigate();
  const { success, error: showError } = useToast();
  const { isAuthenticated } = useAuth();
  const [websiteId, setWebsiteId] = useState("");
  const [websites, setWebsites] = useState([]);
  const [runs, setRuns] = useState([]);
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const previousStatusRef = useRef({});

  async function loadData(forceRefresh = false) {
    setError("");
    setIsBusy(true);
    try {
      const [websiteData, runData] = await Promise.all([websitesService.list(), scansService.listRuns(forceRefresh)]);
      setWebsites(websiteData);
      setRuns(runData);
      if (!websiteId && websiteData.length > 0) {
        setWebsiteId(websiteData[0].id);
      }
    } catch (loadError) {
      setError(loadError.message || "Could not load scans data");
    } finally {
      setIsBusy(false);
    }
  }

  async function enqueueScan() {
    if (!websiteId) {
      setError("Please select a website first.");
      return;
    }

    setError("");
    setIsBusy(true);
    try {
      await scansService.enqueue({ website_id: websiteId });
      await loadData(true);
    } catch (enqueueError) {
      setError(enqueueError.message || "Could not enqueue scan");
      setIsBusy(false);
    }
  }

  async function deleteScan(scanRunId) {
    setError("");
    setIsBusy(true);
    try {
      await scansService.remove(scanRunId);
      success("Scan deleted successfully");
      await loadData(true);
    } catch (deleteError) {
      setError(deleteError.message || "Could not delete scan run");
      setIsBusy(false);
    }
  }

  async function deleteAllScans() {
    const confirmed = window.confirm("Delete all scan history for this tenant? This will remove related findings and alerts too.");
    if (!confirmed) {
      return;
    }

    setError("");
    setIsBusy(true);
    try {
      await scansService.removeAll();
      await loadData(true);
    } catch (deleteError) {
      setError(deleteError.message || "Could not delete scan history");
      setIsBusy(false);
    }
  }

  useEffect(() => {
    loadData(true);
  }, []);

  useEffect(() => {
    const session = localStorage.getItem("authSession");
    const parsedSession = session ? JSON.parse(session) : null;
    const source = createEventSource(`${appConfig.apiBaseUrl}/events/scans/stream`, {
      session: parsedSession,
    });

    source.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload?.runs) {
        setRuns((current) => {
          const updated = new Map(current.map((run) => [run.id, run]));
          for (const remote of payload.runs) {
            const previous = previousStatusRef.current[remote.id];
            const next = { ...updated.get(remote.id), ...remote };
            updated.set(remote.id, next);

            if (
              previous &&
              previous !== "completed" &&
              previous !== "failed" &&
              (next.status === "completed" || next.status === "failed")
            ) {
              if (next.status === "completed") {
                success(`Scan finished successfully for website ${next.website_id}`);
              } else {
                showError(`Scan failed for website ${next.website_id}`);
              }
            }

            previousStatusRef.current[remote.id] = next.status;
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

  const websiteMap = new Map(websites.map((website) => [website.id, website.domain]));

  return (
    <section className="page-card">
      <h2>Scans</h2>
      <p className="hint">Enqueue scans and inspect scan run history.</p>

      <div className="control-row">
        <select value={websiteId} onChange={(event) => setWebsiteId(event.target.value)} disabled={!isAuthenticated}>
          <option value="">Select website</option>
          {websites.map((website) => (
            <option key={website.id} value={website.id}>
              {website.domain}
            </option>
          ))}
        </select>
        <button type="button" onClick={enqueueScan} disabled={isBusy || !isAuthenticated}>Run Scan</button>
        <button type="button" onClick={loadData} disabled={isBusy || !isAuthenticated}>Refresh</button>
      </div>

      <div className="dashboard-actions scans-actions">
        <button type="button" className="danger-button" onClick={deleteAllScans} disabled={isBusy || runs.length === 0 || !isAuthenticated}>
          Delete all scan history
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="list-grid">
        {runs.map((run) => (
          <article key={run.id}>
            <h4>{run.status}</h4>
            <p><strong>Scan ID:</strong> {run.id}</p>
            <p><strong>Website:</strong> {websiteMap.get(run.website_id) || run.website_id}</p>
            <p><strong>Started:</strong> {formatTimestamp(run.started_at)}</p>
            <p><strong>Finished:</strong> {formatTimestamp(run.completed_at)}</p>
              <div className="card-actions">
                <button type="button" onClick={() => navigate(appConfig.routes.scanDetails.replace(":scanId", run.id))} disabled={!isAuthenticated}>
                  View details
                </button>
                <button type="button" className="danger-button" onClick={() => deleteScan(run.id)} disabled={isBusy || !isAuthenticated}>
                  Delete scan
                </button>
              </div>
          </article>
        ))}
        {!runs.length && !isBusy && <p className="hint">No scan runs yet.</p>}
      </div>
    </section>
  );
}
