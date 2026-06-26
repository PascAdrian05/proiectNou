import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { alertsService } from "../services/api/alertsService";
import { behaviorService } from "../services/api/behaviorService";
import { billingService } from "../services/api/billingService";
import { findingsService } from "../services/api/findingsService";
import { presenceService } from "../services/api/presenceService";
import { reportService } from "../services/api/reportService";
import { scansService } from "../services/api/scansService";
import { tenantService } from "../services/api/tenantService";
import { userService } from "../services/api/userService";
import { websitesService } from "../services/api/websitesService";
import { appConfig } from "../config/appConfig";
import { buildAlertFeed, buildSevenDayTrend, buildWebsiteInsights, getTopIssues } from "../utils/dashboardMetrics";
import { exportReportCsv } from "../utils/reportExport";
import { exportReportPdf } from "../utils/reportExportPdf";
import { BehaviorRiskCard } from "../components/BehaviorRiskCard";
import { SecurityScoreCard } from "../components/SecurityScoreCard";
import { SeverityBadge } from "../components/SeverityBadge";
import { StatCard } from "../components/StatCard";

export function DashboardPage() {
  const navigate = useNavigate();
  const { auth } = useAuth();
  const toast = useToast();
  const [websites, setWebsites] = useState([]);
  const [findings, setFindings] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [scans, setScans] = useState([]);
  const [onlineUsers, setOnlineUsers] = useState(0);
  const [profile, setProfile] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [alertsConfigured, setAlertsConfigured] = useState(true);
  const [shareLink, setShareLink] = useState("");
  const [shareExpiresAt, setShareExpiresAt] = useState("");
  const [brandingForm, setBrandingForm] = useState({
    brand_name: "",
    brand_logo_url: "",
    report_primary_color: "#c74634",
    report_base_url: "",
    report_cta_text: "Request Full Access",
    report_cta_url: "",
  });
  const [behaviorRisk, setBehaviorRisk] = useState({
    risk_score: 0,
    risk_level: "low",
    reasons: [],
    event_count: 0,
    event_breakdown: {},
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadDashboard() {
      setError("");
      setIsLoading(true);
      try {
        const [websiteData, findingData, alertData, scanData, presenceData, behaviorData, tenantSettings, profileData, subscriptionData] = await Promise.all([
          websitesService.list(),
          findingsService.list(),
          alertsService.list(),
          scansService.listRuns(),
          presenceService.online(),
          behaviorService.getScore(),
          tenantService.getSettings(),
          userService.getProfile(),
          billingService.getSubscription(),
        ]);

        if (!isMounted) {
          return;
        }

        if (websiteData.length === 0) {
          navigate(appConfig.routes.onboarding, { replace: true });
          return;
        }

        setWebsites(websiteData);
        setFindings(findingData);
        setAlerts(alertData);
        setScans(scanData);
        setOnlineUsers(Number(presenceData?.online_users || 0));
        setBehaviorRisk(behaviorData || behaviorRisk);
        setProfile(profileData);
        setSubscription(subscriptionData);
        setAlertsConfigured(Boolean(tenantSettings?.alert_email || tenantSettings?.alert_webhook_url));
        setBrandingForm({
          brand_name: tenantSettings?.brand_name || tenantSettings?.name || "",
          brand_logo_url: tenantSettings?.brand_logo_url || "",
          report_primary_color: tenantSettings?.report_primary_color || "#c74634",
          report_base_url: tenantSettings?.report_base_url || "",
          report_cta_text: tenantSettings?.report_cta_text || "Request Full Access",
          report_cta_url: tenantSettings?.report_cta_url || "",
        });
      } catch (loadError) {
        if (isMounted) {
          setError(loadError.message || "Could not load dashboard analytics");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadDashboard();
    return () => {
      isMounted = false;
    };
  }, [navigate]);

  useEffect(() => {
    let isMounted = true;

    async function loadOnlineUsers() {
      try {
        const data = await presenceService.online();
        if (isMounted) {
          setOnlineUsers(Number(data?.online_users || 0));
        }
      } catch {
        // presence is best-effort
      }
    }

    const intervalId = window.setInterval(loadOnlineUsers, 10000);
    loadOnlineUsers();

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadBehaviorRisk() {
      try {
        const data = await behaviorService.getScore();
        if (isMounted) {
          setBehaviorRisk(data || behaviorRisk);
        }
      } catch {
        // behavior scoring is best-effort
      }
    }

    const intervalId = window.setInterval(loadBehaviorRisk, 10000);
    loadBehaviorRisk();

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const websiteInsights = useMemo(() => buildWebsiteInsights(websites, findings, scans), [websites, findings, scans]);
  const topIssues = useMemo(() => getTopIssues(findings, 5), [findings]);
  const trend = useMemo(() => buildSevenDayTrend(findings), [findings]);
  const alertFeed = useMemo(() => buildAlertFeed(alerts, findings, websites, 5), [alerts, findings, websites]);
  const averageScore = websiteInsights.length
    ? Math.round(websiteInsights.reduce((total, item) => total + item.score, 0) / websiteInsights.length)
    : 100;

  const criticalCount = findings.filter((f) => String(f.severity).toLowerCase() === "critical").length;
  const openFindings = findings.filter((f) => (f.status || "open") === "open").length;

  function onExportCsv() {
    exportReportCsv({ insights: websiteInsights, topIssues, alerts: alertFeed });
    toast.success("CSV report downloaded.");
  }

  function onExportPdf() {
    exportReportPdf({ 
      insights: websiteInsights, 
      topIssues, 
      alerts: alertFeed,
      tenantName: brandingForm.brand_name || "Security Monitor"
    });
    toast.success("PDF report downloaded.");
  }

  async function onCreateShareLink() {
    try {
      const data = await reportService.createShareLink();
      const publicUrl = data.share_url?.startsWith("http") ? data.share_url : `${window.location.origin}${data.share_url}`;
      setShareLink(publicUrl);
      setShareExpiresAt(data.expires_at || "");
      await navigator.clipboard.writeText(publicUrl);
      toast.success("Share link copied to clipboard.");
    } catch (shareError) {
      setError(shareError.message || "Could not create share link");
      toast.error(shareError.message || "Could not create share link");
    }
  }

  async function onSaveBranding(event) {
    event.preventDefault();
    try {
      await tenantService.updateSettings(brandingForm);
      toast.success("Branding settings saved.");
    } catch (saveError) {
      setError(saveError.message || "Could not save branding settings");
      toast.error(saveError.message || "Could not save branding settings");
    }
  }

  return (
    <section className="page-card">
      <div className="list-header">
        <div>
          <h2>Dashboard</h2>
          <p className="hint">Security operations overview for your tenant.</p>
        </div>
        <div className="dashboard-actions">
          <button type="button" onClick={onExportCsv}>CSV Report</button>
          <button type="button" onClick={onExportPdf}>PDF Report</button>
          <button type="button" onClick={onCreateShareLink}>Share report</button>
        </div>
      </div>
      {shareLink && (
        <div className="share-box">
          <p><strong>Share link:</strong> {shareLink}</p>
          <p className="hint">Expires at: {shareExpiresAt || "7 days from now"}</p>
        </div>
      )}
      {error && <p className="error-text">{error}</p>}
      {!alertsConfigured && !isLoading && (
        <div className="alert-nudge">
          <p><strong>Alerts not configured.</strong> You won't be notified when something breaks — set up email or Slack now.</p>
          <button type="button" onClick={() => navigate(appConfig.routes.settings)}>Configure alerts</button>
        </div>
      )}
      {isLoading && <p className="route-loader">Loading dashboard analytics...</p>}

      <div className="kpi-row">
        <SecurityScoreCard score={averageScore} trend={trend} />
        <StatCard label="Websites" value={websiteInsights.length} hint="Monitored domains" />
        <StatCard label="Open Findings" value={openFindings} hint={`${criticalCount} critical`} accent={criticalCount > 0 ? "bad" : undefined} />
        <StatCard label="Live Users" value={onlineUsers} hint="Active sessions now" accent="good" />
      </div>

      <div className="dashboard-grid">
        <article>
          <h3>Account</h3>
          <p><strong>Email:</strong> {profile?.email || "—"}</p>
          <p><strong>Role:</strong> {auth.role || profile?.role || "n/a"}</p>
          <p><strong>Plan:</strong> {(subscription?.plan || "free").toUpperCase()} ({subscription?.status || "active"})</p>
          <button type="button" className="ghost-button" onClick={() => navigate(appConfig.routes.billing)}>
            Manage billing
          </button>
        </article>
        <BehaviorRiskCard
          score={behaviorRisk.risk_score}
          level={behaviorRisk.risk_level}
          reasons={behaviorRisk.reasons}
          eventCount={behaviorRisk.event_count}
          breakdown={behaviorRisk.event_breakdown}
        />
        <article>
          <h3>Quick Actions</h3>
          <div className="quick-actions-grid">
            <button type="button" className="quick-action-btn" onClick={() => navigate(appConfig.routes.websites)}>
              <span className="quick-action-icon">➕</span>
              <span className="quick-action-label">Add Website</span>
            </button>
            <button type="button" className="quick-action-btn" onClick={() => navigate(appConfig.routes.scans)}>
              <span className="quick-action-icon">🔍</span>
              <span className="quick-action-label">Run Scan</span>
            </button>
            <button type="button" className="quick-action-btn" onClick={onExportPdf}>
              <span className="quick-action-icon">📊</span>
              <span className="quick-action-label">Generate Report</span>
            </button>
            <button type="button" className="quick-action-btn" onClick={onCreateShareLink}>
              <span className="quick-action-icon">🔗</span>
              <span className="quick-action-label">Share Dashboard</span>
            </button>
          </div>
        </article>
        <article>
          <h3>Trend: 7 Days</h3>
          <div className="trend-bars">
            {trend.points.map((point) => (
              <div key={point.key} className="trend-bar-item">
                <div className="trend-bar-label">{point.label}</div>
                <div className="trend-bar-track">
                  <span className="trend-bar-fill" style={{ height: `${Math.max(10, point.count * 18)}px` }} />
                </div>
                <div className="trend-bar-value">{point.count}</div>
              </div>
            ))}
          </div>
        </article>
      </div>

      <div className="dashboard-grid dashboard-grid-wide">
        <article>
          <h3>Public Report Branding</h3>
          <form className="form-grid" onSubmit={onSaveBranding}>
            <label>
              Brand name
              <input value={brandingForm.brand_name} onChange={(event) => setBrandingForm((prev) => ({ ...prev, brand_name: event.target.value }))} />
            </label>
            <label>
              Logo URL
              <input value={brandingForm.brand_logo_url} onChange={(event) => setBrandingForm((prev) => ({ ...prev, brand_logo_url: event.target.value }))} />
            </label>
            <label>
              Primary color
              <input value={brandingForm.report_primary_color} onChange={(event) => setBrandingForm((prev) => ({ ...prev, report_primary_color: event.target.value }))} />
            </label>
            <label>
              Custom report base URL
              <input value={brandingForm.report_base_url} onChange={(event) => setBrandingForm((prev) => ({ ...prev, report_base_url: event.target.value }))} placeholder="https://reports.yourbrand.com" />
            </label>
            <label>
              CTA text
              <input value={brandingForm.report_cta_text} onChange={(event) => setBrandingForm((prev) => ({ ...prev, report_cta_text: event.target.value }))} />
            </label>
            <label>
              CTA URL
              <input value={brandingForm.report_cta_url} onChange={(event) => setBrandingForm((prev) => ({ ...prev, report_cta_url: event.target.value }))} placeholder="https://yourbrand.com/contact" />
            </label>
            <button type="submit">Save branding</button>
          </form>
        </article>
        <article>
          <h3>Website Security Scoreboard</h3>
          <div className="list-grid compact-grid">
            {websiteInsights.map((entry) => (
              <article key={entry.website.id}>
                <h4>{entry.website.domain}</h4>
                <p><strong>Score:</strong> {entry.score}/100</p>
                <p><strong>Status:</strong> {entry.healthLabel}</p>
                <p><strong>Last scan:</strong> {entry.lastScanStatus}</p>
              </article>
            ))}
            {!websiteInsights.length && !isLoading && <p className="hint">Add websites and run scans to compute scores.</p>}
          </div>
        </article>

        <article>
          <h3>Top 5 Problems</h3>
          <div className="issue-list">
            {topIssues.map((issue) => (
              <div key={issue.id} className="issue-item">
                <p><strong>{issue.humanTitle}</strong> <SeverityBadge severity={issue.severity} /></p>
                <p className="hint">{issue.humanSummary}</p>
              </div>
            ))}
            {!topIssues.length && !isLoading && <p className="hint">No issues detected yet.</p>}
          </div>
        </article>

        <article>
          <h3>Alert Feed</h3>
          <div className="issue-list">
            {alertFeed.map((alert) => (
              <div key={alert.id} className="issue-item">
                <p><strong>{alert.websiteDomain}</strong> - {alert.findingTitle}</p>
                <p>{alert.channel} to {alert.recipient}</p>
                <p className="hint">{alert.status} · {alert.relativeTime}</p>
              </div>
            ))}
            {!alertFeed.length && !isLoading && <p className="hint">No recent alerts.</p>}
          </div>
        </article>
      </div>
    </section>
  );
}
