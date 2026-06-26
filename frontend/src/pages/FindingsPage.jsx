import { useEffect, useMemo, useState } from "react";
import { findingsService } from "../services/api/findingsService";
import { websitesService } from "../services/api/websitesService";
import { aiService } from "../services/api/aiService";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";
import { FindingCard } from "../components/FindingCard";
import { QuickFixes } from "../components/QuickFixes";
import { enrichFinding } from "../utils/findingLabels";
import { createEventSource } from "../services/api/eventStream";

const SEVERITY_OPTIONS = ["all", "critical", "high", "medium", "low", "info"];

export function FindingsPage() {
  const toast = useToast();
  const { isAuthenticated } = useAuth();
  const [findings, setFindings] = useState([]);
  const [websites, setWebsites] = useState([]);
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [aiResults, setAiResults] = useState({});
  const [aiLoading, setAiLoading] = useState({});

  async function loadFindings() {
    setError("");
    setIsBusy(true);
    try {
      const [findingData, websiteData] = await Promise.all([
        findingsService.list(),
        websitesService.list(),
      ]);
      setFindings(findingData);
      setWebsites(websiteData);
    } catch (loadError) {
      setError(loadError.message || "Could not load findings");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    loadFindings();
  }, []);

  useEffect(() => {
    const session = localStorage.getItem("authSession");
    const parsedSession = session ? JSON.parse(session) : null;
    const source = createEventSource(`/api/v1/events/findings/stream`, {
      session: parsedSession,
    });

    source.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload?.findings) {
        setFindings((current) => {
          const updated = new Map(current.map((finding) => [finding.id, finding]));
          for (const remote of payload.findings) {
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

  const websiteMap = useMemo(
    () => new Map(websites.map((website) => [String(website.id), website.domain])),
    [websites],
  );

  const filteredFindings = useMemo(() => {
    const query = search.trim().toLowerCase();
    return findings.filter((finding) => {
      const enriched = enrichFinding(finding);
      const matchesSearch =
        !query ||
        enriched.humanTitle.toLowerCase().includes(query) ||
        enriched.humanSummary.toLowerCase().includes(query) ||
        String(finding.kind || "").toLowerCase().includes(query) ||
        String(websiteMap.get(String(finding.website_id)) || "").toLowerCase().includes(query);

      const matchesSeverity =
        severityFilter === "all" ||
        String(finding.severity || "").toLowerCase() === severityFilter;

      const matchesStatus =
        statusFilter === "all" ||
        String(finding.status || "open").toLowerCase() === statusFilter;

      return matchesSearch && matchesSeverity && matchesStatus;
    });
  }, [findings, search, severityFilter, statusFilter, websiteMap]);

  async function deleteFinding(findingId) {
    const confirmed = window.confirm("Delete this finding and its related alerts?");
    if (!confirmed) {
      return;
    }

    setError("");
    setIsBusy(true);
    try {
      await findingsService.remove(findingId);
      await loadFindings();
      toast.success("Finding deleted.");
    } catch (deleteError) {
      setError(deleteError.message || "Could not delete finding");
      toast.error(deleteError.message || "Could not delete finding");
      setIsBusy(false);
    }
  }

  async function onAnalyzeFinding(findingId) {
    setAiLoading((prev) => ({ ...prev, [findingId]: true }));
    setAiResults((prev) => ({ ...prev, [findingId]: null }));
    try {
      const data = await aiService.analyzeFinding(findingId);
      setAiResults((prev) => ({ ...prev, [findingId]: data }));
      if (!data.available) {
        toast.error(data.message || "AI analysis unavailable");
      }
    } catch (err) {
      setAiResults((prev) => ({ ...prev, [findingId]: { available: false, message: err.message || "Analysis failed" } }));
      toast.error(err.message || "AI analysis failed");
    } finally {
      setAiLoading((prev) => ({ ...prev, [findingId]: false }));
    }
  }

  return (
    <section className="page-card">
      <div className="list-header">
        <h2>Findings</h2>
        <button type="button" onClick={loadFindings} disabled={isBusy || !isAuthenticated}>Refresh</button>
      </div>
      <p className="hint">Clear explanations and step-by-step fixes for every security issue.</p>

      <div className="control-row filters-row">
        <input
          type="search"
          placeholder="Search by title, site, kind..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
          {SEVERITY_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option === "all" ? "All severities" : option}
            </option>
          ))}
        </select>
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="all">All statuses</option>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      <p className="hint">{filteredFindings.length} of {findings.length} findings shown</p>
      {error && <p className="error-text">{error}</p>}

      <QuickFixes findings={findings} />

        <div className="findings-list">
          {filteredFindings.map((finding) => {
            const aiResult = aiResults[finding.id];
            const loading = aiLoading[finding.id];
            return (
              <div key={finding.id} className="finding-row">
                <div className="finding-with-ai">
                  <FindingCard
                    finding={finding}
                    websiteDomain={websiteMap.get(String(finding.website_id))}
                  />
                  {aiResult && (
                    <div className={`ai-finding-result ${aiResult.available ? "" : "ai-finding-unavailable"}`}>
                      {aiResult.available ? (
                        <div className="ai-finding-content">
                          <p><strong>Summary:</strong> {aiResult.summary}</p>
                          <p><strong>Severity assessment:</strong> {aiResult.severity_assessment}</p>
                          <p><strong>Recommendation:</strong> {aiResult.recommendation}</p>
                          <p className="ai-hint"><strong>Confidence:</strong> {aiResult.confidence}</p>
                          {aiResult.references && (
                            <p className="ai-hint"><strong>References:</strong> {aiResult.references}</p>
                          )}
                        </div>
                      ) : (
                        <p className="error-text">{aiResult.message}</p>
                      )}
                    </div>
                  )}
                  {loading && (
                    <div className="ai-finding-loading">
                      <span className="ai-typing" aria-hidden="true">
                        <span className="ai-dot" />
                        <span className="ai-dot" />
                        <span className="ai-dot" />
                      </span>
                      <span>AI is analyzing this finding...</span>
                    </div>
                  )}
                </div>
                <div className="card-actions">
                  <button type="button" onClick={() => onAnalyzeFinding(finding.id)} disabled={loading || isBusy || !isAuthenticated}>
                    {loading ? "Analyzing..." : "AI Analyze"}
                  </button>
                  <button type="button" className="danger-button" onClick={() => deleteFinding(finding.id)} disabled={isBusy || loading || !isAuthenticated}>
                    Delete finding
                  </button>
                </div>
              </div>
            );
          })}
          {!filteredFindings.length && !isBusy && <p className="hint">No findings match your filters.</p>}
        </div>
    </section>
  );
}
