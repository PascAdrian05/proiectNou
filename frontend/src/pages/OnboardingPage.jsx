import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FindingCard } from "../components/FindingCard";
import { StatCard } from "../components/StatCard";
import { useToast } from "../context/ToastContext";
import { findingsService } from "../services/api/findingsService";
import { scansService } from "../services/api/scansService";
import { websitesService } from "../services/api/websitesService";
import { appConfig } from "../config/appConfig";
import { parseDomainInput } from "../utils/findingLabels";
import { buildWebsiteInsights } from "../utils/dashboardMetrics";

const SCAN_STEPS = [
  "Connecting to your website...",
  "Checking SSL certificate...",
  "Analyzing security headers...",
  "Scanning exposed ports...",
  "Calculating your security score...",
];

export function OnboardingPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [step, setStep] = useState("welcome");
  const [domainInput, setDomainInput] = useState("");
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanLabel, setScanLabel] = useState(SCAN_STEPS[0]);
  const [website, setWebsite] = useState(null);
  const [findings, setFindings] = useState([]);
  const [scans, setScans] = useState([]);

  useEffect(() => {
    let isMounted = true;

    async function checkExisting() {
      try {
        const websites = await websitesService.list();
        if (isMounted && websites.length > 0) {
          navigate(appConfig.routes.dashboard, { replace: true });
        }
      } catch {
        // stay on onboarding
      }
    }

    checkExisting();
    return () => {
      isMounted = false;
    };
  }, [navigate]);

  useEffect(() => {
    if (step !== "scanning") {
      return undefined;
    }

    let index = 0;
    const intervalId = window.setInterval(() => {
      index = Math.min(index + 1, SCAN_STEPS.length - 1);
      setScanProgress(Math.round(((index + 1) / SCAN_STEPS.length) * 90));
      setScanLabel(SCAN_STEPS[index]);
    }, 2200);

    return () => window.clearInterval(intervalId);
  }, [step]);

  async function pollScanCompletion(scanRunId, websiteId) {
    const maxAttempts = 45;
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const runs = await scansService.listRuns(true);
      const current = runs.find((run) => String(run.id) === String(scanRunId));
      if (current?.status === "completed" || current?.status === "failed") {
        const [findingData, websiteData] = await Promise.all([
          findingsService.list(true),
          websitesService.list(),
        ]);
        setScans(runs);
        setFindings(findingData.filter((f) => String(f.website_id) === String(websiteId)));
        setWebsite(websiteData.find((w) => w.id === websiteId) || null);
        setScanProgress(100);
        setScanLabel(current.status === "completed" ? "Scan complete!" : "Scan finished with errors");
        return current;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 2000));
    }
    throw new Error("Scan is taking longer than expected. Check the Scans page in a moment.");
  }

  async function onStartScan(event) {
    event.preventDefault();
    setError("");

    const parsed = parseDomainInput(domainInput);
    if (!parsed) {
      setError("Enter a valid domain like example.com or https://example.com");
      return;
    }

    setIsBusy(true);
    setStep("scanning");
    setScanProgress(5);
    setScanLabel(SCAN_STEPS[0]);

    try {
      const created = await websitesService.create({
        domain: parsed.domain,
        url: parsed.url,
        scan_frequency_minutes: 1440,
      });

      const job = await scansService.enqueue({ website_id: created.id });
      await pollScanCompletion(job.scan_run_id, created.id);
      setStep("results");
      toast.success("Your first security scan is complete!");
    } catch (startError) {
      setError(startError.message || "Could not complete onboarding scan");
      setStep("welcome");
      toast.error(startError.message || "Could not complete onboarding scan");
    } finally {
      setIsBusy(false);
    }
  }

  const insights = useMemo(
    () => (website ? buildWebsiteInsights([website], findings, scans) : []),
    [website, findings, scans],
  );
  const score = insights[0]?.score ?? 100;
  const healthLabel = insights[0]?.healthLabel ?? "Healthy";

  return (
    <section className="page-card onboarding-shell">
      <div className="onboarding-progress">
        <span className={step === "welcome" ? "active" : ""}>1. Your site</span>
        <span className={step === "scanning" ? "active" : ""}>2. Scanning</span>
        <span className={step === "results" ? "active" : ""}>3. Results</span>
      </div>

      {step === "welcome" && (
        <div className="onboarding-step">
          <h2>Welcome! Let's scan your first website.</h2>
          <p className="hint">
            Enter your domain and we'll run a full security check in under a minute — SSL, headers, uptime, and exposed ports.
          </p>
          <form className="form-grid onboarding-form" onSubmit={onStartScan}>
            <label>
              Website domain
              <input
                type="text"
                placeholder="example.com"
                value={domainInput}
                onChange={(event) => setDomainInput(event.target.value)}
                required
                autoFocus
              />
              <span className="field-hint">We'll check https://your-domain automatically.</span>
            </label>
            <button type="submit" disabled={isBusy}>
              {isBusy ? "Starting..." : "Scan my website"}
            </button>
          </form>
          {error && <p className="error-text">{error}</p>}
        </div>
      )}

      {step === "scanning" && (
        <div className="onboarding-step onboarding-scanning">
          <h2>Scanning {website?.domain || parseDomainInput(domainInput)?.domain || "your site"}...</h2>
          <p className="hint">{scanLabel}</p>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${scanProgress}%` }} />
          </div>
          <p className="hint progress-percent">{scanProgress}%</p>
        </div>
      )}

      {step === "results" && (
        <div className="onboarding-step">
          <h2>Your security report is ready</h2>
          <p className="hint">
            {website?.domain} scored <strong>{score}/100</strong> — {healthLabel.toLowerCase()}.
            {findings.length === 0
              ? " No issues found. We'll keep monitoring automatically."
              : ` We found ${findings.length} issue${findings.length === 1 ? "" : "s"} to address.`}
          </p>

          <div className="kpi-row onboarding-kpi">
            <StatCard
              label="Security Score"
              value={`${score}/100`}
              hint={healthLabel}
              accent={score >= 85 ? "good" : score >= 65 ? "warn" : "bad"}
            />
            <StatCard label="Issues found" value={findings.length} hint="From first scan" accent={findings.length ? "bad" : "good"} />
          </div>

          {findings.length > 0 && (
            <div className="onboarding-findings">
              <h3>What we found</h3>
              {findings.map((finding) => (
                <FindingCard key={finding.id} finding={finding} websiteDomain={website?.domain} />
              ))}
            </div>
          )}

          <div className="onboarding-cta">
            <button type="button" onClick={() => navigate(appConfig.routes.settings)}>
              Set up alerts
            </button>
            <button type="button" className="ghost-button" onClick={() => navigate(appConfig.routes.dashboard)}>
              Go to dashboard
            </button>
          </div>
          <p className="hint onboarding-tip">
            Tip: Configure email or Slack alerts so you're notified instantly — you won't need to check the dashboard every day.
          </p>
        </div>
      )}
    </section>
  );
}
