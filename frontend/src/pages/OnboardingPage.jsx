import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { FindingCard } from "../components/FindingCard";
import { StatCard } from "../components/StatCard";
import { ScanRadarEffect } from "../components/ScanRadarEffect";
import { useToast } from "../context/ToastContext";
import { subscribeToScanEvents } from "../services/api/eventStream";
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

const ONBOARDING_STEPS = [
  { id: "welcome", label: "1. Welcome", description: "Learn about Security Monitor" },
  { id: "add-site", label: "2. Add Site", description: "Add your first website" },
  { id: "scanning", label: "3. Scanning", description: "Security scan in progress" },
  { id: "results", label: "4. Results", description: "Review your security score" },
  { id: "alerts", label: "5. Alerts", description: "Set up notifications" },
  { id: "complete", label: "6. Complete", description: "Ready to go" },
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
  const [alertEmail, setAlertEmail] = useState("");
  const [alertWebhook, setAlertWebhook] = useState("");

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

  const wsCleanupRef = useRef(null);

  useEffect(() => {
    if (step !== "scanning") return undefined;

    let index = 0;
    const intervalId = window.setInterval(() => {
      index = Math.min(index + 1, SCAN_STEPS.length - 1);
      setScanProgress(Math.round(((index + 1) / SCAN_STEPS.length) * 90));
      setScanLabel(SCAN_STEPS[index]);
    }, 2200);

    wsCleanupRef.current = subscribeToScanEvents({
      onProgress: (data) => {
        if (data.progress) {
          const pct = Math.round((data.progress.steps_completed / data.progress.total_steps) * 100);
          setScanProgress(pct);
          setScanLabel(SCAN_STEPS[data.progress.steps_completed] || SCAN_STEPS[0]);
        }
      },
      onCompleted: (data) => {
        setScanProgress(100);
        setScanLabel(data.status === "completed" ? "Scan complete!" : "Scan finished with errors");
      },
    });

    return () => {
      window.clearInterval(intervalId);
      if (wsCleanupRef.current) wsCleanupRef.current();
    };
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

  const pageVariants = {
    initial: { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -12 },
  };

  return (
    <section className="page-card onboarding-shell">
      <div className="onboarding-progress">
        {ONBOARDING_STEPS.map((s) => (
          <motion.span
            key={s.id}
            className={step === s.id ? "active" : ONBOARDING_STEPS.findIndex((x) => x.id === step) > ONBOARDING_STEPS.findIndex((x) => x.id === s.id) ? "done" : ""}
            title={s.description}
            layout
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
          >
            {ONBOARDING_STEPS.findIndex((x) => x.id === step) > ONBOARDING_STEPS.findIndex((x) => x.id === s.id) ? "\u2713 " : ""}{s.label}
          </motion.span>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={step} variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.18, ease: "easeOut" }}>

      {step === "welcome" && (
        <div className="onboarding-step">
          <h2>Welcome to Security Monitor <span role="img" aria-label="shield">🛡️</span></h2>
          <p className="hint">
            We'll help you set up continuous security monitoring for your websites in just a few minutes.
          </p>
          <div className="onboarding-features">
            <h3>What you'll get:</h3>
            <ul>
              <li><span role="img" aria-label="check">✅</span> Automated security scans (SSL, headers, ports)</li>
              <li><span role="img" aria-label="check">✅</span> Real-time security scoring</li>
              <li><span role="img" aria-label="check">✅</span> AI-powered security insights</li>
              <li><span role="img" aria-label="check">✅</span> Instant alerts via email or webhooks</li>
              <li><span role="img" aria-label="check">✅</span> Beautiful shareable security reports</li>
            </ul>
          </div>
          <button type="button" onClick={() => setStep("add-site")}>
            Get Started →
          </button>
        </div>
      )}

      {step === "add-site" && (
        <div className="onboarding-step">
          <h2>Add your first website</h2>
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
          <button type="button" className="ghost-button" onClick={() => setStep("welcome")}>
            ← Back
          </button>
        </div>
      )}

      {step === "scanning" && (
        <div className="onboarding-step onboarding-scanning">
          <ScanRadarEffect active />
          <h2>Scanning {website?.domain || parseDomainInput(domainInput)?.domain || "your site"}</h2>
          <p className="hint">{scanLabel}</p>
          <div className="progress-track">
            <motion.div
              className="progress-fill"
              initial={{ width: "0%" }}
              animate={{ width: `${scanProgress}%` }}
              transition={{ duration: 0.4, ease: "easeOut" }}
            />
          </div>
          <motion.p
            className="hint progress-percent"
            key={scanProgress}
            initial={{ opacity: 0.4, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.15 }}
          >
            {scanProgress}%
          </motion.p>
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
            <motion.div className="onboarding-findings" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
              <h3>What we found</h3>
              {findings.map((finding, i) => (
                <motion.div key={finding.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 + i * 0.1 }}>
                  <FindingCard finding={finding} websiteDomain={website?.domain} />
                </motion.div>
              ))}
            </motion.div>
          )}

          <div className="onboarding-cta">
            <button type="button" onClick={() => setStep("alerts")}>
              Set up alerts →
            </button>
            <button type="button" className="ghost-button" onClick={() => navigate(appConfig.routes.dashboard)}>
              Skip for now
            </button>
          </div>
        </div>
      )}

      {step === "alerts" && (
        <div className="onboarding-step">
          <h2>Set up alerts (optional)</h2>
          <p className="hint">
            Get notified instantly when we find security issues. You can always configure this later in Settings.
          </p>
          <form className="form-grid onboarding-form" onSubmit={(e) => { e.preventDefault(); setStep("complete"); }}>
            <label>
              Email for alerts
              <input
                type="email"
                placeholder="you@example.com"
                value={alertEmail}
                onChange={(event) => setAlertEmail(event.target.value)}
              />
              <span className="field-hint">We'll send security alerts here</span>
            </label>
            <label>
              Webhook URL (optional)
              <input
                type="url"
                placeholder="https://hooks.slack.com/..."
                value={alertWebhook}
                onChange={(event) => setAlertWebhook(event.target.value)}
              />
              <span className="field-hint">For Slack, Discord, or custom integrations</span>
            </label>
            <button type="submit">
              Complete setup →
            </button>
          </form>
          <button type="button" className="ghost-button" onClick={() => setStep("results")}>
            ← Back
          </button>
        </div>
      )}

      {step === "complete" && (
        <div className="onboarding-step">
          <h2>You're all set! <span role="img" aria-label="party">🎉</span></h2>
          <p className="hint">
            Your website is now being monitored continuously. We'll scan it regularly and alert you to any issues.
          </p>
          <div className="onboarding-complete-info">
            <h3>What happens next:</h3>
            <ul>
              <li><span role="img" aria-label="sync">🔄</span> Automatic scans will run periodically</li>
              <li><span role="img" aria-label="chart">📊</span> Your security score will update automatically</li>
              <li><span role="img" aria-label="bell">🔔</span> You'll receive alerts if issues are found</li>
              <li><span role="img" aria-label="trend">📈</span> Track trends in your dashboard</li>
              <li><span role="img" aria-label="robot">🤖</span> Use AI Assistant for security insights</li>
            </ul>
          </div>
          <div className="onboarding-cta">
            <button type="button" onClick={() => navigate(appConfig.routes.dashboard)}>
              Go to Dashboard →
            </button>
          </div>
          <p className="hint onboarding-tip">
            Pro tip: Enable 2FA in Settings for enhanced account security.
          </p>
        </div>
      )}

        </motion.div>
      </AnimatePresence>
    </section>
  );
}
