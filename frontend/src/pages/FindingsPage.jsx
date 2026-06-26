import { useState, useEffect, useCallback } from "react";
import { toast } from "react-hot-toast";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  AlertTriangle, Bug, Info, Shield, ExternalLink, ChevronDown, ChevronRight,
  Globe, RefreshCw, Search
} from "lucide-react";
import { findingsService } from "../services/api/findingsService";
import { scansService } from "../services/api/scansService";
import { websitesService } from "../services/api/websitesService";
import { formatDistanceToNow } from "../lib/utils";

const severityConfig = {
  critical: { icon: AlertTriangle, color: "text-error", bg: "bg-error/10", border: "border-error/30", badge: "badge-error" },
  high: { icon: AlertTriangle, color: "text-warning", bg: "bg-warning/10", border: "border-warning/30", badge: "badge-warning" },
  medium: { icon: Bug, color: "text-info", bg: "bg-info/10", border: "border-info/30", badge: "badge-info" },
  low: { icon: Info, color: "text-base-content/60", bg: "bg-base-200", border: "border-base-300", badge: "badge-ghost" },
};

export function FindingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [findings, setFindings] = useState([]);
  const [websites, setWebsites] = useState([]);
  const [websiteId, setWebsiteId] = useState(searchParams.get("website_id") || "");
  const [scanId, setScanId] = useState(searchParams.get("scan_id") || "");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await websitesService.list();
        if (!cancelled) setWebsites(data);
      } catch {}
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const loadFindings = useCallback(async () => {
    setLoading(true);
    try {
      const data = await findingsService.list();
      setFindings(data || []);
    } catch (err) {
      if (err.status !== 404) {
        toast.error("Eroare la incarcarea constatarilor.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  function handleWebsiteChange(wid) {
    setWebsiteId(wid);
    setScanId("");
    setSeverityFilter("all");
    const params = new URLSearchParams(searchParams);
    if (wid) params.set("website_id", wid); else params.delete("website_id");
    params.delete("scan_id");
    setSearchParams(params, { replace: true });
  }

  function handleScanChange(sid) {
    setScanId(sid);
    const params = new URLSearchParams(searchParams);
    if (sid) params.set("scan_id", sid); else params.delete("scan_id");
    setSearchParams(params, { replace: true });
  }

  // Filter findings client-side
  const filteredFindings = findings.filter((f) => {
    if (websiteId && f.website_id !== websiteId) return false;
    if (scanId && f.scan_run_id !== scanId) return false;
    if (severityFilter !== "all" && f.severity !== severityFilter) return false;
    return true;
  });

  async function handleRefresh() {
    await loadFindings();
    toast.success("Lista actualizata");
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Constatari</h1>
          <p className="text-base-content/60">
            {findings.length > 0
              ? `${filteredFindings.length} din ${findings.length} constatari`
              : "Vulnerabilitati descoperite in scanari"}
          </p>
        </div>
        <button className="btn btn-outline btn-sm" onClick={handleRefresh} disabled={loading}>
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="card bg-base-100 shadow-lg">
        <div className="card-body p-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <label className="form-control flex-1">
              <div className="label py-0 pb-1">
                <span className="label-text text-xs">Site</span>
              </div>
              <select className="select select-bordered select-sm w-full" value={websiteId} onChange={(e) => handleWebsiteChange(e.target.value)}>
                <option value="">Toate site-urile</option>
                {websites.map((w) => (
                  <option key={w.id} value={w.id}>{w.domain || w.url}</option>
                ))}
              </select>
            </label>
          </div>

          {findings.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {["critical", "high", "medium", "low"].map((sev) => {
                const cfg = severityConfig[sev];
                const count = findings.filter((f) => f.severity === sev).length;
                if (count === 0) return null;
                return (
                  <button
                    key={sev}
                    onClick={() => setSeverityFilter(severityFilter === sev ? "all" : sev)}
                    className={`badge ${cfg.badge} gap-1 cursor-pointer transition-all hover:scale-105 ${severityFilter === sev ? "ring-2 ring-offset-1 ring-base-content/40" : "badge-outline"}`}
                  >
                    {count} {sev}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <span className="loading loading-spinner loading-lg text-primary" />
        </div>
      ) : filteredFindings.length === 0 ? (
        <div className="card bg-base-100 shadow-lg">
          <div className="card-body items-center text-center py-16">
            <Shield className={`w-10 h-10 ${findings.length > 0 ? "text-success" : "text-base-content/30"} mb-4`} />
            <h2 className="text-xl font-bold">
              {findings.length > 0 ? "Nicio constatare cu acest filtru" : "Nicio constatare gasita"}
            </h2>
            <p className="text-base-content/60 max-w-md mt-2">
              {findings.length > 0
                ? "Incearca sa elimini filtrele aplicate."
                : "Efectueaza o scanare pentru a descoperi vulnerabilitati."}
            </p>
            {findings.length === 0 && (
              <button className="btn btn-primary mt-6" onClick={() => navigate("/scans")}>
                <Search className="w-4 h-4" /> Mergi la Scanari
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="grid gap-3">
          {filteredFindings.map((finding) => {
            const cfg = severityConfig[finding.severity] || severityConfig.low;
            const Icon = cfg.icon;

            return (
              <div
                key={finding.id}
                className={`card bg-base-100 shadow-lg border-l-4 ${cfg.border} hover:shadow-xl transition-all`}
              >
                <div className="card-body p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <div className={`p-2 rounded-lg ${cfg.bg} mt-0.5 shrink-0`}>
                        <Icon className={`w-5 h-5 ${cfg.color}`} />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold truncate">{finding.title}</span>
                          <span className={`badge badge-sm ${cfg.badge}`}>{finding.severity}</span>
                          <span className="badge badge-sm badge-ghost">{finding.kind || "general"}</span>
                        </div>
                        <p className="text-sm text-base-content/60 mt-0.5">
                          {finding.created_at && formatDistanceToNow(finding.created_at)}
                          {finding.status && finding.status !== "open" && (
                            <span className="ml-2 badge badge-sm badge-ghost">{finding.status}</span>
                          )}
                        </p>
                      </div>
                    </div>
                    <a
                      href={`/findings/${finding.id}`}
                      className="btn btn-ghost btn-sm btn-square"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default FindingsPage;
