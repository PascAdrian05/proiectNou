import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authService } from "../services/api/authService";
import { useAuth } from "../context/AuthContext";
import { authFormDefaults } from "../data/mock/authMock";
import { appConfig } from "../config/appConfig";
import { PasswordField } from "../components/PasswordField";

export function RegisterPage() {
  const navigate = useNavigate();
  const { saveSession } = useAuth();
  const [form, setForm] = useState(authFormDefaults.register);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const payload = {
        // TODO: Bind your API data here if backend field names change.
        tenant_name: form.tenantName,
        email: form.email,
        password: form.password,
      };

      const response = await authService.register(payload);
      saveSession({
        accessToken: response.access_token,
        refreshToken: response.refresh_token || "",
        role: response.role || "",
        tenantId: response.tenant_id || "",
      });
      navigate(appConfig.routes.onboarding);
    } catch (submitError) {
      setError(submitError.message || "Registration failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="page-card">
      <h2>Register</h2>
      <p className="hint">Create a tenant and owner account in one step.</p>

      <form onSubmit={onSubmit} className="form-grid">
        <label>
          Tenant Name
          <input
            type="text"
            placeholder="Acme Security"
            value={form.tenantName}
            onChange={(event) => setForm((prev) => ({ ...prev, tenantName: event.target.value }))}
            minLength={2}
            maxLength={120}
            required
          />
        </label>

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
          placeholder="Minimum 8 characters"
          value={form.password}
          onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
          minLength={8}
          maxLength={128}
          required
        />

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating account..." : "Register"}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}

      <p className="hint">
        Already have an account? <Link to={appConfig.routes.login}>Go to login</Link>
      </p>
    </section>
  );
}
