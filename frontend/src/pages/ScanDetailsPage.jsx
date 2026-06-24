import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { appConfig } from "../config/appConfig";
import { scansService } from "../services/api/scansService";
import { websitesService } from "../services/api/websitesService";

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

function parseResultPayload(value) {
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function DetailRow({ label, value }) {
  return (
    <p>
      <strong>{label}:</strong> {String(value ?? "n/a")}
    </p>
  );
}

export function ScanDetailsPage() {
  const { scanId } = useParams();
  const [scan, setScan] = useState(null);
  const [websites, setWebsites] = useState([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadScanDetails() {
      setError("");
      setIsLoading(true);
      try {
        const [runs, websiteData] = await Promise.all([
          scansService.listRuns(true),
          websitesService.list(),
        ]);

        if (!isMounted) {
          return;
        }

        const currentScan = runs.find((entry) => entry.id === scanId);
        if (!currentScan) {
          setError("Scan not found");
        }
        setScan(currentScan || null);
        setWebsites(websiteData);
      } catch (loadError) {
        if (isMounted) {
          setError(loadError.message || "Could not load scan details");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadScanDetails();
    return () => {
      isMounted = false;
    };
  }, [scanId]);

  useEffect(() => {
    if (!scan || (scan.status !== "pending" && scan.status !== "running")) {
      return undefined;
    }

    const intervalId = window.setInterval(async () => {
      try {
        const runs = await scansService.listRuns(true);
        const currentScan = runs.find((entry) => entry.id === scanId);
        if (currentScan) {
          setScan(currentScan);
        }
      } catch {
        // keep previous state until next manual refresh
      }
    }, 4000);

    return () => window.clearInterval(intervalId);
  }, [scan, scanId]);

  const websiteName = useMemo(() => {
    if (!scan) {
      return "n/a";
    }
    return websites.find((website) => website.id === scan.website_id)?.domain || scan.website_id;
  }, [scan, websites]);

  const result = useMemo(() => parseResultPayload(scan?.result_json), [scan]);

  return (
    <section className="page-card">
      <div className="list-header">
        <h2>Scan Details</h2>
        <Link className="back-link" to={appConfig.routes.scans}>Back to scans</Link>
      </div>
      <p className="hint">Full execution view for one scan run: metadata, health checks, TLS result, headers, ports, raw payload, and errors.</p>
      {isLoading && <p className="route-loader">Loading scan details...</p>}
      {error && <p className="error-text">{error}</p>}

      {scan && (
        <div className="dashboard-grid dashboard-grid-wide">
          <article>
            <h3>Execution Metadata</h3>
            <DetailRow label="Scan ID" value={scan.id} />
            <DetailRow label="Website" value={websiteName} />
            <DetailRow label="Status" value={scan.status} />
            <DetailRow label="Started" value={formatTimestamp(scan.started_at)} />
            <DetailRow label="Finished" value={formatTimestamp(scan.completed_at)} />
            <DetailRow label="Created" value={formatTimestamp(scan.created_at)} />
          </article>

          <article>
            <h3>Failure / Error</h3>
            <p className="hint">If the scan task crashes, the backend writes the exact error message here.</p>
            <pre className="result-box">{scan.error_message || "No error recorded"}</pre>
          </article>

          <article>
            <h3>Uptime Check</h3>
            <DetailRow label="Reachable" value={result?.uptime?.reachable ?? "n/a"} />
            <DetailRow label="HTTP Status" value={result?.uptime?.status_code ?? "n/a"} />
            <DetailRow label="Latency (ms)" value={result?.uptime?.latency_ms ?? "n/a"} />
            <pre className="result-box">{JSON.stringify(result?.uptime || {}, null, 2)}</pre>
          </article>

          <article>
            <h3>TLS / SSL Check</h3>
            <DetailRow label="Valid" value={result?.ssl_expiry?.valid ?? "n/a"} />
            <DetailRow label="Expires At" value={result?.ssl_expiry?.expires_at ?? "n/a"} />
            <DetailRow label="Days Left" value={result?.ssl_expiry?.days_left ?? "n/a"} />
            <pre className="result-box">{JSON.stringify(result?.ssl_expiry || {}, null, 2)}</pre>
          </article>

          <article>
            <h3>Security Headers</h3>
            <DetailRow label="Score" value={result?.security_headers?.score ?? "n/a"} />
            <DetailRow label="Missing Count" value={result?.security_headers?.missing?.length ?? 0} />
            <pre className="result-box">{JSON.stringify(result?.security_headers || {}, null, 2)}</pre>
          </article>

          <article>
            <h3>Port Exposure</h3>
            <DetailRow label="Open Ports" value={(result?.open_ports?.open_ports || []).join(", ") || "none"} />
            <pre className="result-box">{JSON.stringify(result?.open_ports || {}, null, 2)}</pre>
          </article>

          <article>
            <h3>Raw Scan Payload</h3>
            <p className="hint">This is the exact serialized result returned by the worker and persisted in the database.</p>
            <pre className="result-box">{scan.result_json || "No payload recorded"}</pre>
          </article>
        </div>
      )}
    </section>
  );
}
