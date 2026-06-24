import { useEffect, useState } from "react";
import { tenantService } from "../services/api/tenantService";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";

export function SettingsPage() {
  const toast = useToast();
  const { isAuthenticated } = useAuth();
  const [form, setForm] = useState({
    alert_email: "",
    alert_webhook_url: "",
    brand_name: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);

  async function loadSettings() {
    setError("");
    setIsLoading(true);
    try {
      const data = await tenantService.getSettings();
      setForm({
        alert_email: data.alert_email || "",
        alert_webhook_url: data.alert_webhook_url || "",
        brand_name: data.brand_name || data.name || "",
      });
    } catch (loadError) {
      setError(loadError.message || "Could not load settings");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadSettings();
  }, []);

  async function onSave(event) {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    try {
      await tenantService.updateSettings({
        alert_email: form.alert_email || null,
        alert_webhook_url: form.alert_webhook_url || null,
        brand_name: form.brand_name || null,
      });
      toast.success("Alert settings saved. You'll be notified on the next finding.");
    } catch (saveError) {
      setError(saveError.message || "Could not save settings");
      toast.error(saveError.message || "Could not save settings");
    } finally {
      setIsSaving(false);
    }
  }

  async function onTestAlert() {
    if (!form.alert_email && !form.alert_webhook_url) {
      toast.error("Add an email or webhook URL first.");
      return;
    }

    setIsTesting(true);
    setError("");
    try {
      await tenantService.updateSettings({
        alert_email: form.alert_email || null,
        alert_webhook_url: form.alert_webhook_url || null,
        brand_name: form.brand_name || null,
      });
      await tenantService.sendTestAlert();
      toast.success("Test alert sent! Check your inbox or Slack channel.");
    } catch (testError) {
      setError(testError.message || "Could not send test alert");
      toast.error(testError.message || "Could not send test alert");
    } finally {
      setIsTesting(false);
    }
  }

  return (
    <section className="page-card">
      <h2>Settings</h2>
      <p className="hint">
        Configure where you receive alerts when a scan finds a problem. This is how the app keeps you coming back — not by checking the dashboard daily.
      </p>

      {isLoading && <p className="route-loader">Loading settings...</p>}
      {error && <p className="error-text">{error}</p>}

      {!isLoading && (
        <form className="form-grid settings-form" onSubmit={onSave} aria-disabled={!isAuthenticated}>
          <label>
            Organization name
            <input
              value={form.brand_name}
              onChange={(event) => setForm((prev) => ({ ...prev, brand_name: event.target.value }))}
              placeholder="Acme Security"
            />
          </label>

          <label>
            Alert email
            <input
              type="email"
              value={form.alert_email}
              onChange={(event) => setForm((prev) => ({ ...prev, alert_email: event.target.value }))}
              placeholder="you@company.com"
            />
            <span className="field-hint">We'll email you when a critical or high finding is detected.</span>
          </label>

          <label>
            Slack / webhook URL
            <input
              type="url"
              value={form.alert_webhook_url}
              onChange={(event) => setForm((prev) => ({ ...prev, alert_webhook_url: event.target.value }))}
              placeholder="https://hooks.slack.com/services/..."
            />
            <span className="field-hint">Optional. Paste a Slack incoming webhook or any JSON endpoint.</span>
          </label>

          <div className="settings-actions">
            <button type="submit" disabled={isSaving || !isAuthenticated}>
              {isSaving ? "Saving..." : "Save settings"}
            </button>
            <button type="button" className="ghost-button" onClick={onTestAlert} disabled={isTesting || !isAuthenticated}>
              {isTesting ? "Sending..." : "Send test alert"}
            </button>
          </div>
        </form>
      )}

      <div className="settings-info">
        <h3>How alerts work</h3>
        <ul>
          <li>Every time a scan finds an issue, we send a notification to your email and/or webhook.</li>
          <li>Alerts include the site name, severity, and what to fix.</li>
          <li>Without alerts configured, you'll need to check the dashboard manually.</li>
        </ul>
      </div>
    </section>
  );
}
