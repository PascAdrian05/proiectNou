import { useEffect, useState } from "react";
import { monitoringDefaults } from "../data/mock/monitoringMock";
import { websitesService } from "../services/api/websitesService";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export function WebsitesPage() {
  const { isAuthenticated } = useAuth();
  const { success, error: showError } = useToast();
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
        domain: form.domain,
        url: form.url,
        scan_frequency_minutes: Number(form.scan_frequency_minutes),
      };
      await websitesService.create(payload);
      success("Website created successfully");
      setForm(monitoringDefaults.websiteForm);
      await loadWebsites();
    } catch (createError) {
      setError(createError.message || "Could not create website");
      showError(createError.message || "Could not create website");
      setIsBusy(false);
    }
  }

  async function deleteWebsite(websiteId) {
    setError("");
    setIsBusy(true);
    try {
      await websitesService.remove(websiteId);
      success("Website deleted successfully");
      await loadWebsites();
    } catch (deleteError) {
      setError(deleteError.message || "Could not delete website");
      showError(deleteError.message || "Could not delete website");
      setIsBusy(false);
    }
  }

  useEffect(() => {
    loadWebsites();
  }, []);

  return (
    <section className="page-card">
      <div className="list-header">
        <div>
          <h2>Websites</h2>
          <p className="hint">Add websites to monitor for security vulnerabilities and compliance issues.</p>
        </div>
        <button type="button" onClick={loadWebsites} disabled={isBusy || !isAuthenticated}>Refresh</button>
      </div>

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
        <label className="auto-scan-toggle">
          <input
            type="checkbox"
            checked={form.scan_frequency_minutes > 0}
            onChange={(e) => setForm((prev) => ({ ...prev, scan_frequency_minutes: e.target.checked ? 1440 : 0 }))}
          />
          <span>Enable auto-scan</span>
        </label>
        {form.scan_frequency_minutes > 0 && (
          <label>
            Scan frequency
            <input
              type="number"
              min={1}
              value={form.scan_frequency_minutes}
              onChange={(event) => setForm((prev) => ({ ...prev, scan_frequency_minutes: event.target.value }))}
              required
            />
            <span className="field-hint">Minutes between automatic scans.</span>
          </label>
        )}
        <button type="submit" disabled={isBusy || !isAuthenticated}>{isBusy ? "Creating..." : "Add Website"}</button>
      </form>

      {error && <p className="error-text">{error}</p>}

      <div className="list-grid">
        {websites.map((website) => (
          <article key={website.id}>
            <h4>{website.domain}</h4>
            <p><strong>URL:</strong> {website.url}</p>
            <p><strong>Scan Frequency:</strong> Every {website.scan_frequency_minutes} minute{website.scan_frequency_minutes !== 1 ? 's' : ''}</p>
            <div className="card-actions">
              <button type="button" className="danger-button" onClick={() => deleteWebsite(website.id)} disabled={isBusy || !isAuthenticated}>
                Delete
              </button>
            </div>
          </article>
        ))}
        {!websites.length && !isBusy && <p className="hint">No websites monitored yet. Add a website above to start security monitoring.</p>}
      </div>
    </section>
  );
}
