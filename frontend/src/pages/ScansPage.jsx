import { useState, useEffect, useCallback, useRef } from "react";
import { toast } from "react-hot-toast";
import { Plus, Globe, Activity, Clock, Shield, Search, X, AlertTriangle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { scansService } from "../services/api/scansService";
import { websitesService } from "../services/api/websitesService";
import { formatDistanceToNow } from "../lib/utils";

export function ScansPage() {
  const { auth } = useAuth();
  const [websites, setWebsites] = useState([]);
  const [scans, setScans] = useState([]);
  const [websiteId, setWebsiteId] = useState("");
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanningProgress, setScanningProgress] = useState(null);
  const [showAddWebsite, setShowAddWebsite] = useState(false);
  const [addUrl, setAddUrl] = useState("");
  const [addingWebsite, setAddingWebsite] = useState(false);
  const pollRef = useRef(null);

  // Load websites once
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await websitesService.list();
        if (!cancelled) setWebsites(data);
      } catch {
        if (!cancelled) toast.error("Nu s-au putut incarca site-urile.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const loadScans = useCallback(async () => {
    try {
      const data = await scansService.listRuns();
      setScans(data || []);
    } catch {
      toast.error("Nu s-au putut incarca scanarile.");
    }
  }, []);

  useEffect(() => {
    loadScans();
  }, [loadScans]);

  async function handleAddWebsite(e) {
    e.preventDefault();
    if (!addUrl.trim()) return;
    setAddingWebsite(true);
    try {
      const domain = addUrl.trim().replace(/^https?:\/\//, "").replace(/\/.*$/, "");
      const newWebsite = await websitesService.create({
        domain,
        url: addUrl.trim(),
      });
      setWebsites((prev) => [...prev, newWebsite]);
      setWebsiteId(newWebsite.id);
      setAddUrl("");
      setShowAddWebsite(false);
      toast.success(`Site adaugat: ${newWebsite.domain || domain}`);
    } catch (err) {
      toast.error(err.message || "Eroare la adaugarea site-ului.");
    } finally {
      setAddingWebsite(false);
    }
  }

  async function handleStartScan() {
    if (!websiteId) return;
    setScanning(true);
    setScanningProgress(null);
    try {
      await scansService.enqueue({ website_id: websiteId });
      toast.success("Scanare pornita!");
      loadScans();
      startPolling();
    } catch (err) {
      setScanning(false);
      toast.error(err.message || "Eroare la pornirea scanarii.");
    }
  }

  function startPolling() {
    stopPolling();
    pollRef.current = window.setInterval(async () => {
      try {
        const data = await scansService.listRuns(true);
        setScans(data || []);
        const running = data?.some((s) => s.status === "running" || s.status === "pending");
        if (!running) {
          stopPolling();
          setScanning(false);
          setScanningProgress(null);
        }
      } catch {
        stopPolling();
        setScanning(false);
      }
    }, 3000);
  }

  function stopPolling() {
    if (pollRef.current) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  useEffect(() => {
    return stopPolling;
  }, []);

  const selectedWebsite = websites.find((w) => w.id === websiteId);
  const websiteScans = websiteId
    ? scans.filter((s) => s.website_id === websiteId)
    : scans;
  const latestScan = websiteScans.length > 0 ? websiteScans[0] : null;

  const statusBadge = {
    completed: "badge-success",
    running: "badge-info",
    pending: "badge-warning",
    failed: "badge-error",
  };

  const scanResult = {
    completed: { icon: Shield, text: "Finalizata", color: "text-success" },
    running: { icon: Activity, text: "In desfasurare", color: "text-info" },
    pending: { icon: Clock, text: "In asteptare", color: "text-warning" },
    failed: { icon: AlertTriangle, text: "Esuata", color: "text-error" },
  };

  return (
    <div className="space-y-6">
      {showAddWebsite && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-base-300/80 backdrop-blur-sm" onClick={() => setShowAddWebsite(false)}>
          <div className="card w-full max-w-md bg-base-100 shadow-2xl mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="card-body">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-bold">Adauga Site</h3>
                <button className="btn btn-ghost btn-sm btn-square" onClick={() => setShowAddWebsite(false)}>
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleAddWebsite} className="space-y-4">
                <label className="form-control">
                  <div className="label">
                    <span className="label-text">URL-ul site-ului</span>
                  </div>
                  <input
                    type="url"
                    placeholder="https://exemplu.ro"
                    className="input input-bordered w-full"
                    value={addUrl}
                    onChange={(e) => setAddUrl(e.target.value)}
                    required
                    disabled={addingWebsite}
                  />
                </label>
                <button type="submit" className="btn btn-primary w-full" disabled={addingWebsite || !addUrl.trim()}>
                  {addingWebsite ? <span className="loading loading-spinner" /> : <Plus className="w-4 h-4" />}
                  {addingWebsite ? "Se adauga..." : "Adauga"}
                </button>
              </form>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Scanari</h1>
          <p className="text-base-content/60">Gestioneaza scanarile de securitate</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowAddWebsite(true)}>
          <Plus className="w-4 h-4" />
          Adauga Site
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <span className="loading loading-spinner loading-lg text-primary" />
        </div>
      ) : websites.length === 0 ? (
        <div className="card bg-base-100 shadow-lg">
          <div className="card-body items-center text-center py-16">
            <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Globe className="w-10 h-10 text-primary" />
            </div>
            <h2 className="text-xl font-bold">Niciun site adaugat</h2>
            <p className="text-base-content/60 max-w-md mt-2">
              Adauga un site pentru a incepe scanarile de securitate.
            </p>
            <button className="btn btn-primary mt-6" onClick={() => setShowAddWebsite(true)}>
              <Plus className="w-4 h-4" /> Adauga primul site
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="card bg-base-100 shadow-lg">
            <div className="card-body">
              <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
                <label className="form-control flex-1 w-full">
                  <div className="label">
                    <span className="label-text">Selecteaza site-ul</span>
                  </div>
                  <select
                    className="select select-bordered w-full"
                    value={websiteId}
                    onChange={(e) => setWebsiteId(e.target.value)}
                  >
                    <option value="">-- Alege un site --</option>
                    {websites.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.domain || w.url}
                      </option>
                    ))}
                  </select>
                </label>

                {websiteId && (
                  <button
                    className="btn btn-primary w-full sm:w-auto"
                    onClick={handleStartScan}
                    disabled={scanning}
                  >
                    {scanning ? (
                      <span className="loading loading-spinner loading-sm" />
                    ) : (
                      <Search className="w-4 h-4" />
                    )}
                    {scanning ? "Se scaneaza..." : "Porneste scanarea"}
                  </button>
                )}
              </div>

              {scanningProgress != null && (
                <div className="mt-4">
                  <div className="flex justify-between text-sm mb-1">
                    <span>Progres</span>
                    <span>{Math.round(scanningProgress)}%</span>
                  </div>
                  <progress className="progress progress-primary w-full" value={scanningProgress} max="100" />
                </div>
              )}

              {selectedWebsite && (
                <div className="flex flex-wrap gap-2 mt-3">
                  <div className="badge badge-outline gap-1">
                    <Globe className="w-3 h-3" />
                    {selectedWebsite.domain || selectedWebsite.url}
                  </div>
                  {latestScan && (
                    <div className="badge badge-outline gap-1">
                      <Activity className="w-3 h-3" />
                      Ultima: {formatDistanceToNow(latestScan.created_at)}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {!websiteId ? (
            <div className="card bg-base-100 shadow-lg">
              <div className="card-body items-center text-center py-12">
                <Search className="w-8 h-8 text-base-content/40 mb-3" />
                <p className="text-base-content/60">Selecteaza un site</p>
              </div>
            </div>
          ) : websiteScans.length === 0 && !scanning ? (
            <div className="card bg-base-100 shadow-lg">
              <div className="card-body items-center text-center py-12">
                <Shield className="w-8 h-8 text-base-content/40 mb-3" />
                <p className="text-base-content/60">Nicio scanare pentru acest site</p>
                <button className="btn btn-primary btn-sm mt-4" onClick={handleStartScan}>
                  <Search className="w-4 h-4" /> Prima scanare
                </button>
              </div>
            </div>
          ) : (
            <div className="grid gap-4">
              {websiteScans.map((scan) => {
                const result = scanResult[scan.status] || scanResult.pending;
                const Icon = result.icon;
                return (
                  <div key={scan.id} className="card bg-base-100 shadow-lg hover:shadow-xl transition-shadow">
                    <div className="card-body p-5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg bg-base-200 ${result.color}`}>
                            <Icon className="w-5 h-5" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-semibold">Scanare</span>
                              <span className={`badge badge-sm ${statusBadge[scan.status] || "badge-ghost"}`}>
                                {scan.status}
                              </span>
                            </div>
                            <p className="text-sm text-base-content/60">
                              {formatDistanceToNow(scan.created_at)}
                            </p>
                          </div>
                        </div>
                        <a
                          href={`/findings?scan_id=${scan.id}`}
                          className="btn btn-ghost btn-sm"
                        >
                          Vezi constatarile
                        </a>
                      </div>
                      {scan.progress && scan.status === "running" && (
                        <div className="mt-3">
                          <progress className="progress progress-primary w-full" value={0} max="100" />
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ScansPage;
