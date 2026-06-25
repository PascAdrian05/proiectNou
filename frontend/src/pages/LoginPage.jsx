import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authService } from "../services/api/authService";
import { websitesService } from "../services/api/websitesService";
import { useAuth } from "../context/AuthContext";
import { authFormDefaults } from "../data/mock/authMock";
import { appConfig } from "../config/appConfig";
import { PasswordField } from "../components/PasswordField";

export function LoginPage() {
  const navigate = useNavigate();
  const { saveSession } = useAuth();
  const [form, setForm] = useState(authFormDefaults.login);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 2FA state
  const [requires2FA, setRequires2FA] = useState(false);
  const [twoFactorToken, setTwoFactorToken] = useState("");

  // Recovery state
  const [showRecovery, setShowRecovery] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await authService.login(form.email, form.password);

      // Check if 2FA is required
      if (response.requires_2fa) {
        setRequires2FA(true);
        setError("");
        setIsSubmitting(false);
        return;
      }

      // No 2FA required, normal login
      saveSession({
        accessToken: response.access_token,
        refreshToken: response.refresh_token || "",
        role: response.role || "",
        tenantId: response.tenant_id || "",
      });

      try {
        const websites = await websitesService.list();
        navigate(websites.length ? appConfig.routes.dashboard : appConfig.routes.onboarding);
      } catch {
        navigate(appConfig.routes.onboarding);
      }
    } catch (submitError) {
      setError(submitError.message || "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function onVerify2FA(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await authService.verify2fa(form.email, form.password, twoFactorToken);

      saveSession({
        accessToken: response.access_token,
        refreshToken: response.refresh_token || "",
        role: response.role || "",
        tenantId: response.tenant_id || "",
      });

      try {
        const websites = await websitesService.list();
        navigate(websites.length ? appConfig.routes.dashboard : appConfig.routes.onboarding);
      } catch {
        navigate(appConfig.routes.onboarding);
      }
    } catch (verifyError) {
      setError(verifyError.message || "2FA verification failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function onRecoverWithBackup(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const normalizedCode = recoveryCode
        .toUpperCase()
        .replace(/\s/g, "")
        .replace(/-/g, "");

      const formattedCode = `${normalizedCode.slice(0, 4)}-${normalizedCode.slice(4)}`;
      const response = await authService.recoverWithBackupCode(form.email, form.password, formattedCode);

      saveSession({
        accessToken: response.access_token,
        refreshToken: response.refresh_token || "",
        role: response.role || "",
        tenantId: response.tenant_id || "",
      });

      try {
        const websites = await websitesService.list();
        navigate(websites.length ? appConfig.routes.dashboard : appConfig.routes.onboarding);
      } catch {
        navigate(appConfig.routes.onboarding);
      }
    } catch (recoverError) {
      setError(recoverError.message || "Backup code recovery failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  function onCancel2FA() {
    setRequires2FA(false);
    setTwoFactorToken("");
    setShowRecovery(false);
    setRecoveryCode("");
    setError("");
  }

  function switchToRecovery() {
    setShowRecovery(true);
    setError("");
  }

  function switchTo2FA() {
    setShowRecovery(false);
    setError("");
  }

  return (
    <section className="page-card">
      <h2>Login</h2>
      <p className="hint">
        {requires2FA && !showRecovery
          ? "Enter your 2FA code to complete login."
          : requires2FA && showRecovery
            ? "Enter one of your backup codes to recover access."
            : "Authenticate with your tenant account credentials."}
      </p>

      {!requires2FA ? (
        <form onSubmit={onSubmit} className="form-grid">
          <label>
            Email
            <input
              type="email"
              placeholder="owner@example.com"
              value={form.email}
              onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
              required
            />
          </label>

          <PasswordField
            label="Password"
            placeholder="Enter your password"
            value={form.password}
            onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
            required
          />

          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Login"}
          </button>
        </form>
      ) : showRecovery ? (
        <form onSubmit={onRecoverWithBackup} className="form-grid">
          <label>
            Backup Code
            <input
              type="text"
              placeholder="ABCD-1234"
              value={recoveryCode}
              onChange={(event) => setRecoveryCode(event.target.value.toUpperCase().slice(0, 9))}
              required
              autoFocus
            />
            <span className="field-hint">
              Enter one of your 10 backup codes. Each code can only be used once.
            </span>
          </label>

          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Recovering..." : "Recover Access"}
          </button>

          <div className="settings-actions">
            <button type="button" className="ghost-button" onClick={switchTo2FA}>
              Use authenticator app instead
            </button>
            <button type="button" className="ghost-button" onClick={onCancel2FA}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <form onSubmit={onVerify2FA} className="form-grid">
          <label>
            2FA Code
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]{6}"
              placeholder="000000"
              value={twoFactorToken}
              onChange={(event) => setTwoFactorToken(event.target.value.replace(/\D/g, "").slice(0, 6))}
              required
              maxLength={6}
              autoFocus
            />
            <span className="field-hint">Enter the 6-digit code from your authenticator app.</span>
          </label>

          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Verifying..." : "Verify"}
          </button>

          <div className="settings-actions">
            <button type="button" className="ghost-button" onClick={switchToRecovery}>
              Use a backup code instead
            </button>
            <button type="button" className="ghost-button" onClick={onCancel2FA}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {error && <p className="error-text">{error}</p>}

      {!requires2FA && (
        <p className="hint">
          New here? <Link to={appConfig.routes.register}>Create an account</Link>
        </p>
      )}
    </section>
  );
}