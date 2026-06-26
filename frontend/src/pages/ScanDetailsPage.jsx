import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { appConfig } from "../config/appConfig";
import { scansService } from "../services/api/scansService";
import { websitesService } from "../services/api/websitesService";
import { subscribeToScanEvents } from "../services/api/eventStream";
import { ScanProgress } from "../components/ScanProgress";

function formatTimestamp(value) {
  if (!value) return "n/a";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function parseResultPayload(value) {
  if (!value) return null;
  try { return JSON.parse(value); } catch { return null; }
}

function DetailRow({ label, value }) {
  return <p><strong>{label}:</strong> {String(value ?? "n/a")}</p>;
}

export function ScanDetailsPage() {
  const { scanId } = useParams();
  const [scan, setScan] = useState(null);
  const [websites, setWebsites] = useState([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

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
        if (!isMounted) return;
        const currentScan = runs.find((entry) => entry.id === scanId);
        if (!currentScan) setError("Scan not found");
        setScan(currentScan || null);
        setWebsites(websiteData);
      } catch (loadError) {
        if (isMounted) setError(loadError.message || "Could not load scan details");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadScanDetails();

    const cleanup = subscribeToScanEvents({
      onProgress: (data) => {
        if (data.scan_run_id !== scanId) return;
        setScan((prev) => prev ? {
          ...prev,
          status: data.status,
          current_step: data.step,
          progress: data.progress ? JSON.stringify(data.progress) : prev.progress,
        } : prev);
      },
      onCompleted: (data) => {
        if (data.scan_run_id !== scanId) return;
        loadScanDetails();
      },
    });

    return () => {
      isMounted = false;
      if (cleanup) cleanup();
    };
  }, [scanId]);

  const websiteName = useMemo(() => {
    if (!scan) return "n/a";
    return websites.find((w) => w.id === scan.website_id)?.domain || scan.website_id;
  }, [scan, websites]);

  const result = useMemo(() => parseResultPayload(scan?.result_json), [scan]);
  const progress = scan?.progress ? (() => { try { return JSON.parse(scan.progress); } catch { return null; } })() : null;
  const isActive = scan?.status === "running" || scan?.status === "pending";
  const isFinished = scan?.status === "completed" || scan?.status === "failed";

  return (
    <section className="page-card">
      <div className="list-header">
        <h2>Scan Details</h2>
        <Link className="back-link" to={appConfig.routes.scans}>Back to scans</Link>
      </div>
      <p className="hint">
        {isActive ? "Scan is running — results will appear automatically when complete." : "Full execution view for one scan run."}
      </p>

      {isLoading && <p className="route-loader">Loading scan details...</p>}
      {error && <p className="error-text">{error}</p>}

      {(isActive || isFinished) && (
        <ScanProgress
          currentStep={scan?.current_step}
          status={scan?.status}
          stepStatuses={progress?.step_statuses || null}
          scanRunId={scanId}
          onViewDetails={() => {}}
        />
      )}

      {isActive && (
        <motion.div
          className="scan-waiting"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <p className="hint" style={{ textAlign: "center", fontSize: "1.1em", padding: "2rem" }}>
            Scan in progress... Details will appear automatically when completed.
          </p>
        </motion.div>
      )}

      {isFinished && scan && (
        <motion.div
          className="dashboard-grid dashboard-grid-wide"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <article>
            <h3>Execution Metadata</h3>
            <DetailRow label="Scan ID" value={scan.id} />
            <DetailRow label="Website" value={websiteName} />
            <DetailRow label="Status" value={scan.status} />
            <DetailRow label="Started" value={formatTimestamp(scan.started_at)} />
            <DetailRow label="Finished" value={formatTimestamp(scan.completed_at)} />
          </article>

          <article>
            <h3>Failure / Error</h3>
            <pre className="result-box">{scan.error_message || "No error recorded"}</pre>
          </article>

          {result && (
            <>
              <article>
                <h3>Uptime Check</h3>
                <DetailRow label="Reachable" value={result.uptime?.reachable ?? "n/a"} />
                <DetailRow label="HTTP Status" value={result.uptime?.status_code ?? "n/a"} />
                <DetailRow label="Latency (ms)" value={result.uptime?.latency_ms ?? "n/a"} />
                <pre className="result-box">{JSON.stringify(result.uptime || {}, null, 2)}</pre>
              </article>

              <article>
                <h3>TLS / SSL Check</h3>
                <DetailRow label="Valid" value={result.ssl_expiry?.valid ?? "n/a"} />
                <DetailRow label="Expires At" value={result.ssl_expiry?.expires_at ?? "n/a"} />
                <DetailRow label="Days Left" value={result.ssl_expiry?.days_left ?? "n/a"} />
                <pre className="result-box">{JSON.stringify(result.ssl_expiry || {}, null, 2)}</pre>
              </article>

              <article>
                <h3>Security Headers</h3>
                <DetailRow label="Score" value={result.security_headers?.score ?? "n/a"} />
                <DetailRow label="Missing Count" value={result.security_headers?.missing?.length ?? 0} />
                <pre className="result-box">{JSON.stringify(result.security_headers || {}, null, 2)}</pre>
              </article>

              <article>
                <h3>Port Exposure</h3>
                <DetailRow label="Open Ports" value={(result.open_ports?.open_ports || []).join(", ") || "none"} />
                <pre className="result-box">{JSON.stringify(result.open_ports || {}, null, 2)}</pre>
              </article>
            </>
          )}

          <article>
            <h3>Raw Scan Payload</h3>
            <pre className="result-box">{scan.result_json || "No payload recorded"}</pre>
          </article>
        </motion.div>
      )}
    </section>
  );
}
