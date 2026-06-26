import { useState } from "react";
import { Shield } from "lucide-react";
import { authService } from "../services/api/authService";

export default function StepUpModal({ onVerified, onClose }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await authService.stepUp(token);
      onVerified(result.step_up_token);
    } catch (err) {
      setError(err.message || "Verification failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="overlay-panel" role="dialog" aria-modal="true" aria-labelledby="stepup-title">
      <div className="stepup-modal" onClick={(e) => e.stopPropagation()}>
        <div className="stepup-icon">
          <Shield size={24} strokeWidth={2} aria-hidden="true" />
        </div>
        <h2 id="stepup-title">Re-verify your identity</h2>
        <p className="hint">
          This action requires additional verification. Enter the code from your
          authenticator app to continue.
        </p>

        <form onSubmit={handleSubmit} className="form-grid stepup-form">
          <label>
            Authenticator code
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              placeholder="000000"
              value={token}
              onChange={(e) => setToken(e.target.value.replace(/\D/g, "").slice(0, 6))}
              className="stepup-token-input"
              autoFocus
              required
            />
          </label>

          {error && <p className="error-text">{error}</p>}

          <div className="stepup-actions">
            <button type="button" className="ghost-button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" disabled={loading || token.length !== 6}>
              {loading ? "Verifying..." : "Verify"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}