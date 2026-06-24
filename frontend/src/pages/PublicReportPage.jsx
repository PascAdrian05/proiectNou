import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { reportService } from "../services/api/reportService";
import { formatRelativeTime } from "../utils/dashboardMetrics";
import { getHumanTitle } from "../utils/findingLabels";

function SectionCard({ title, children }) {
  return (
    <article>
      <h3>{title}</h3>
      {children}
    </article>
  );
}

export function PublicReportPage() {
  const { shareToken } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadReport() {
      setIsLoading(true);
      try {
        const data = await reportService.fetchSharedReport(shareToken);
        if (isMounted) {
          setReport(data);
        }
      } catch (loadError) {
        if (isMounted) {
          setError(loadError.message || "Could not load shared report");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadReport();
    return () => {
      isMounted = false;
    };
  }, [shareToken]);

  const topWebsite = useMemo(() => {
    if (!report?.websites?.length) {
      return null;
    }
    return [...report.websites].sort((left, right) => right.score - left.score)[0];
  }, [report]);

  return (
    <section className="page-card public-report-shell" style={{ borderTop: `6px solid ${report?.branding?.report_primary_color || "#c74634"}` }}>
      <div className="public-report-header">
        <div>
          <h2>{report?.branding?.brand_name || "Shared Security Report"}</h2>
          <p className="hint">Read-only report generated for a client share link.</p>
        </div>
        {report?.branding?.brand_logo_url && <img className="brand-logo" src={report.branding.brand_logo_url} alt={report.branding.brand_name || "Brand logo"} />}
      </div>
      {isLoading && <p className="route-loader">Loading shared report...</p>}
      {error && <p className="error-text">{error}</p>}

      {report && (
        <div className="dashboard-grid dashboard-grid-wide">
          <SectionCard title="Executive Summary">
            <p className="score-value">{report.security_score}/100</p>
            <p><strong>Behavior risk:</strong> {report.behavior_risk?.risk_level || "low"}</p>
            <p><strong>Generated:</strong> {formatRelativeTime(report.generated_at)}</p>
            <p><strong>Top website:</strong> {topWebsite?.domain || "n/a"}</p>
          </SectionCard>

          <SectionCard title="Top Websites">
            <div className="issue-list">
              {report.websites?.map((website) => (
                <div key={website.id} className="issue-item">
                  <p><strong>{website.domain}</strong></p>
                  <p>Score: {website.score}/100</p>
                  <p className="hint">{website.finding_count} findings</p>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Key Findings">
            <div className="issue-list">
              {report.top_findings?.map((finding) => (
                <div key={finding.id} className="issue-item">
                  <p><strong>{getHumanTitle(finding)}</strong></p>
                  <p>{finding.kind} · {finding.severity}</p>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Behavior Risk">
            <p className="score-value">{report.behavior_risk?.risk_score || 0}/100</p>
            <p><strong>Level:</strong> {report.behavior_risk?.risk_level || "low"}</p>
            <div className="issue-list">
              {report.behavior_risk?.reasons?.map((reason) => (
                <div key={reason} className="issue-item">
                  <p>{reason}</p>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Recent Alerts">
            <div className="issue-list">
              {report.alerts?.map((alert) => (
                <div key={alert.id} className="issue-item">
                  <p><strong>{alert.channel}</strong> · {alert.status}</p>
                  <p>{alert.recipient}</p>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Recent Scan Runs">
            <div className="issue-list">
              {report.scan_runs?.map((scan) => (
                <div key={scan.id} className="issue-item">
                  <p><strong>{scan.status}</strong></p>
                  <p>Started: {scan.started_at || "n/a"}</p>
                  <p>Finished: {scan.completed_at || "n/a"}</p>
                </div>
              ))}
            </div>
          </SectionCard>
        </div>
      )}

      {report?.branding?.report_cta_url && (
        <div className="share-box public-cta-box">
          <p><strong>Need full access or ongoing monitoring?</strong></p>
          <a className="cta-link" href={report.branding.report_cta_url} target="_blank" rel="noreferrer">
            {report.branding.report_cta_text || "Request Full Access"}
          </a>
        </div>
      )}

      <p className="hint">
        This page is public and read-only. Return to <Link to="/login">login</Link>.
      </p>
    </section>
  );
}