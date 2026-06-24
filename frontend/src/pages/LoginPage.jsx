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

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await authService.login(form);
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

  return (
    <section className="page-card">
      <h2>Login</h2>
      <p className="hint">Authenticate with your tenant account credentials.</p>

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

      {error && <p className="error-text">{error}</p>}

      <p className="hint">
        New here? <Link to={appConfig.routes.register}>Create an account</Link>
      </p>
    </section>
  );
}
