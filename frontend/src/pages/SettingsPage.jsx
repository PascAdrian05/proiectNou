import { useEffect, useState } from "react";
import { tenantService } from "../services/api/tenantService";
import { authService } from "../services/api/authService";
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
  
  // 2FA state
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [twoFactorSetupStep, setTwoFactorSetupStep] = useState("none"); // none, setup, verify
  const [twoFactorSecret, setTwoFactorSecret] = useState("");
  const [twoFactorQrCode, setTwoFactorQrCode] = useState("");
  const [twoFactorToken, setTwoFactorToken] = useState("");
  const [twoFactorPassword, setTwoFactorPassword] = useState("");

  // Security status
  const [securityStatus, setSecurityStatus] = useState(null);
  const [backupCodes, setBackupCodes] = useState(null);
  const [backupCodesLoading, setBackupCodesLoading] = useState(false);
  const [backupCodesError, setBackupCodesError] = useState("");

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
      
      // Load 2FA status
      try {
        const securityStatus = await authService.getSecurityStatus();
        setTwoFactorEnabled(securityStatus.totp_enabled || false);
      } catch (securityError) {
        console.error("Could not load security status:", securityError);
      }
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

  // 2FA Functions
  // Load security status
  useEffect(() => {
    if (!isAuthenticated) return;
    authService.getSecurityStatus()
      .then(setSecurityStatus)
      .catch(() => {});
  }, [isAuthenticated, twoFactorEnabled]);

  async function onSetup2FA() {
    setError("");
    try {
      const response = await authService.setup2fa(twoFactorPassword);
      setTwoFactorSecret(response.secret);
      setTwoFactorQrCode(response.qr_code);
      setTwoFactorSetupStep("verify");
    } catch (setupError) {
      setError(setupError.message || "Could not setup 2FA");
      toast.error(setupError.message || "Could not setup 2FA");
    }
  }

  async function onEnable2FA() {
    setError("");
    try {
      await authService.enable2fa(twoFactorSecret, twoFactorToken);
      setTwoFactorEnabled(true);
      setTwoFactorSetupStep("none");
      setTwoFactorToken("");
      setTwoFactorSecret("");
      setTwoFactorQrCode("");
      setTwoFactorPassword("");
      toast.success("2FA enabled successfully!");
    } catch (enableError) {
      setError(enableError.message || "Could not enable 2FA");
      toast.error(enableError.message || "Could not enable 2FA");
    }
  }

  async function onDisable2FA() {
    setError("");
    try {
      await authService.disable2fa(""); // No password required
      setTwoFactorEnabled(false);
      setTwoFactorPassword("");
      toast.success("2FA disabled successfully!");
    } catch (disableError) {
      setError(disableError.message || "Could not disable 2FA");
      toast.error(disableError.message || "Could not disable 2FA");
    }
  }

  function onCancel2FASetup() {
    setTwoFactorSetupStep("none");
    setTwoFactorToken("");
    setTwoFactorSecret("");
    setTwoFactorQrCode("");
    setTwoFactorPassword("");
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

      {/* Security Score */}
      {securityStatus && (
        <div className="settings-section">
          <h3>Security Score</h3>
          <div className="security-score-bar">
            <div className="security-score-fill" style={{ width: `${securityStatus.security_score}%` }} />
          </div>
          <p className="hint">
            Score: <strong>{securityStatus.security_score}%</strong>
            {securityStatus.totp_enabled && " · 2FA: ✅"}
            {securityStatus.passkey_enabled && " · Passkey: ✅"}
            {securityStatus.has_backup_codes && " · Backup codes: ✅"}
            {!securityStatus.security_setup_completed && (
              <span className="text-amber-600"> · Onboarding not completed</span>
            )}
          </p>
        </div>
      )}

      {/* Backup Codes Section */}
      {twoFactorEnabled && (
        <div className="settings-section">
          <h3>Backup Codes</h3>
          <p className="hint">
            Backup codes let you recover access to your account if you lose your authenticator device.
            Each code can only be used once.
          </p>

          {backupCodes ? (
            <div>
              <div className="bg-amber-50 dark:bg-amber-900/20 p-4 rounded-md mb-4">
                <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                  ⚠️ Save these codes now!
                </p>
                <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                  These codes will not be shown again. Store them in a password manager.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2 mb-4">
                {backupCodes.map((code, i) => (
                  <code key={i} className="bg-gray-100 dark:bg-gray-700 px-3 py-2 rounded text-center font-mono text-sm">
                    {code}
                  </code>
                ))}
              </div>
              <button
                type="button"
                className="ghost-button"
                onClick={() => {
                  const content = backupCodes.join("\n");
                  const blob = new Blob([content], { type: "text/plain" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "security-monitor-backup-codes.txt";
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                Download codes
              </button>
              <button
                type="button"
                className="ghost-button ml-2"
                onClick={() => setBackupCodes(null)}
              >
                I've saved them
              </button>
            </div>
          ) : (
            <div className="settings-actions">
              <button
                type="button"
                onClick={async () => {
                  setBackupCodesLoading(true);
                  setBackupCodesError("");
                  try {
                    const result = await authService.generateBackupCodes();
                    setBackupCodes(result.codes);
                  } catch (err) {
                    setBackupCodesError(err.message);
                    toast.error(err.message);
                  } finally {
                    setBackupCodesLoading(false);
                  }
                }}
                disabled={backupCodesLoading}
              >
                {backupCodesLoading ? "Generating..." : "Generate new backup codes"}
              </button>
            </div>
          )}
          {backupCodesError && <p className="error-text">{backupCodesError}</p>}
        </div>
      )}

      {/* 2FA Section */}
      <div className="settings-section">
        <h3>Two-Factor Authentication (2FA)</h3>
        <p className="hint">
          Add an extra layer of security to your account with TOTP-based 2FA.
        </p>

        {twoFactorEnabled ? (
          <div className="two-factor-enabled">
            <p className="success-text">✅ 2FA is currently enabled</p>
            <div className="settings-actions">
              <button
                type="button"
                className="danger-button"
                onClick={onDisable2FA}
                disabled={!isAuthenticated}
              >
                Disable 2FA
              </button>
            </div>
          </div>
        ) : twoFactorSetupStep === "setup" ? (
          <div className="two-factor-setup">
            <p>Enter your password to begin 2FA setup:</p>
            <label>
              Password
              <input
                type="password"
                value={twoFactorPassword}
                onChange={(e) => setTwoFactorPassword(e.target.value)}
                placeholder="Your password"
              />
            </label>
            <div className="settings-actions">
              <button type="button" onClick={onSetup2FA} disabled={!isAuthenticated}>
                Continue
              </button>
              <button type="button" className="ghost-button" onClick={onCancel2FASetup}>
                Cancel
              </button>
            </div>
          </div>
        ) : twoFactorSetupStep === "verify" ? (
          <div className="two-factor-verify">
            <p>Scan this QR code with your authenticator app:</p>
            {twoFactorQrCode && (
              <div className="qr-code-container">
                <img src={twoFactorQrCode} alt="2FA QR Code" />
              </div>
            )}
            <p className="hint">Or enter this secret manually: {twoFactorSecret}</p>
            <label>
              Verification Code
              <input
                type="text"
                value={twoFactorToken}
                onChange={(e) => setTwoFactorToken(e.target.value)}
                placeholder="123456"
                maxLength={6}
              />
            </label>
            <div className="settings-actions">
              <button type="button" onClick={onEnable2FA} disabled={!isAuthenticated}>
                Enable 2FA
              </button>
              <button type="button" className="ghost-button" onClick={onCancel2FASetup}>
                Cancel
              </button>
            </div>
          </div>
        ) : twoFactorSetupStep === "disable" ? (
          <div className="two-factor-disable">
            <p>Enter your password to disable 2FA:</p>
            <label>
              Password
              <input
                type="password"
                value={twoFactorPassword}
                onChange={(e) => setTwoFactorPassword(e.target.value)}
                placeholder="Your password"
              />
            </label>
            <div className="settings-actions">
              <button
                type="button"
                className="danger-button"
                onClick={onDisable2FA}
                disabled={!isAuthenticated}
              >
                Confirm Disable
              </button>
              <button type="button" className="ghost-button" onClick={onCancel2FASetup}>
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="two-factor-disabled">
            <p className="hint">2FA is not enabled. Enable it for enhanced security.</p>
            <div className="settings-actions">
              <button
                type="button"
                onClick={() => setTwoFactorSetupStep("setup")}
                disabled={!isAuthenticated}
              >
                Enable 2FA
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
