import { useEffect, useState } from "react";
import { monitoringDefaults } from "../data/mock/monitoringMock";
import { websitesService } from "../services/api/websitesService";
import { useAuth } from "../context/AuthContext";

export function WebsitesPage() {
  const { isAuthenticated } = useAuth();
  const [form, setForm] = useState(monitoringDefaults.websiteForm);
  const [websites, setWebsites] = useState([]);
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  async function loadWebsites() {
    setError("");
    setIsBusy(true);
    try {
      const data = await websitesService.list();
      setWebsites(data);
    } catch (loadError) {
      setError(loadError.message || "Could not load websites");
    } finally {
      setIsBusy(false);
    }
  }

  async function createWebsite(event) {
    event.preventDefault();
    setError("");
    setIsBusy(true);
    try {
      const payload = {
        // TODO: Bind your API data here if backend payload fields change.
        domain: form.domain,
        url: form.url,
        scan_frequency_minutes: Number(form.scan_frequency_minutes),
      };
      await websitesService.create(payload);
      await loadWebsites();
    } catch (createError) {
      setError(createError.message || "Could not create website");
      setIsBusy(false);
    }
  }

  async function deleteWebsite(websiteId) {
    const confirmed = window.confirm("Delete this website and its related scans, findings, and alerts?");
    if (!confirmed) {
      return;
    }

    setError("");
    setIsBusy(true);
    try {
      await websitesService.remove(websiteId);
      await loadWebsites();
    } catch (deleteError) {
      setError(deleteError.message || "Could not delete website");
      setIsBusy(false);
    }
  }

  useEffect(() => {
    loadWebsites();
  }, []);

  return (
    <section className="page-card">
      <h2>Websites</h2>
      <p className="hint">Create and view monitored websites.</p>

      <form onSubmit={createWebsite} className="form-grid" aria-disabled={!isAuthenticated}>
        <label>
          Domain
          <input
            type="text"
            placeholder="example.com"
            value={form.domain}
            onChange={(event) => setForm((prev) => ({ ...prev, domain: event.target.value }))}
            required
          />
        </label>
        <label>
          URL
          <input
            type="url"
            placeholder="https://example.com"
            value={form.url}
            onChange={(event) => setForm((prev) => ({ ...prev, url: event.target.value }))}
            required
          />
        </label>
        <label>
          Scan Frequency (minutes)
          <input
            type="number"
            min={1}
            value={form.scan_frequency_minutes}
            onChange={(event) => setForm((prev) => ({ ...prev, scan_frequency_minutes: event.target.value }))}
            required
          />
        </label>
        <button type="submit" disabled={isBusy || !isAuthenticated}>{isBusy ? "Saving..." : "Create Website"}</button>
      </form>

      <div className="list-header">
        <h3>Current Websites</h3>
        <button type="button" onClick={loadWebsites} disabled={isBusy || !isAuthenticated}>Refresh</button>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="list-grid">
        {websites.map((website) => (
          <article key={website.id}>
            <h4>{website.domain}</h4>
            <p><strong>URL:</strong> {website.url}</p>
            <p><strong>Frequency:</strong> {website.scan_frequency_minutes} min</p>
            <div className="card-actions">
              <button type="button" className="danger-button" onClick={() => deleteWebsite(website.id)} disabled={isBusy || !isAuthenticated}>
                Delete site
              </button>
            </div>
          </article>
        ))}
        {!websites.length && !isBusy && <p className="hint">No websites yet.</p>}
      </div>
    </section>
  );
}
