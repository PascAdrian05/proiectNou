import { useState, useRef } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { Shield, Eye, EyeOff, Lock, KeyRound } from "lucide-react";
import { toast } from "react-hot-toast";
import { useAuth } from "../context/AuthContext";
import { authService } from "../services/api/authService";
import { providerIcons } from "./OAuthIcons";

const CODE_LENGTH = 6;

function LoginPage() {
  const { isAuthenticated, saveSession } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [pendingToken, setPendingToken] = useState(null);
  const [code, setCode] = useState(Array(CODE_LENGTH).fill(""));
  const [focusedIdx, setFocusedIdx] = useState(0);
  const inputRefs = useRef([]);

  if (isAuthenticated) {
    return <Navigate to={searchParams.get("redirect") || "/"} replace />;
  }

  async function handleLogin(e) {
    e.preventDefault();
    setLoginError("");

    if (!email || !password) {
      setLoginError("Completeaza email si parola.");
      return;
    }

    setLoading(true);
    try {
      const response = await authService.login(email, password);

      if (response.requires_2fa) {
        setPendingToken(response.access_token);
        setFocusedIdx(0);
        setTimeout(() => inputRefs.current[0]?.focus(), 100);
      } else {
        saveSession({
          accessToken: response.access_token,
          refreshToken: response.refresh_token,
          role: response.role,
          tenantId: response.tenant_id,
          email: email,
        });
        toast.success(`Bine ai venit!`);
        navigate(searchParams.get("redirect") || "/");
      }
    } catch (err) {
      const msg = err.message || "Eroare de autentificare";
      if (msg.includes("locked") || msg.includes("temporar")) {
        setLoginError("Cont blocat temporar. Verifica emailul sau contacteaza suportul.");
      } else if (msg.includes("Invalid") || msg.includes("incorect")) {
        setLoginError("Email sau parola incorecte.");
      } else {
        setLoginError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  function handleCodeChange(index, value) {
    const digit = value.replace(/\D/g, "").slice(-1);
    const newCode = [...code];
    newCode[index] = digit;
    setCode(newCode);

    if (digit && index < CODE_LENGTH - 1) {
      setFocusedIdx(index + 1);
      inputRefs.current[index + 1]?.focus();
    }

    const fullCode = newCode.join("");
    if (fullCode.length === CODE_LENGTH) {
      submit2FA(fullCode);
    }
  }

  function handleCodeKeyDown(index, e) {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      setFocusedIdx(index - 1);
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowLeft" && index > 0) {
      setFocusedIdx(index - 1);
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < CODE_LENGTH - 1) {
      setFocusedIdx(index + 1);
      inputRefs.current[index + 1]?.focus();
    }
  }

  function handleCodePaste(e) {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, CODE_LENGTH);
    const newCode = [...code];
    for (let i = 0; i < pasted.length; i++) {
      newCode[i] = pasted[i];
    }
    setCode(newCode);
    const nextIdx = Math.min(pasted.length, CODE_LENGTH - 1);
    setFocusedIdx(nextIdx);
    inputRefs.current[nextIdx]?.focus();

    if (pasted.length === CODE_LENGTH) {
      submit2FA(pasted);
    }
  }

  async function submit2FA(fullCode) {
    if (fullCode.length !== CODE_LENGTH) return;
    setLoading(true);
    try {
      const response = await authService.verify2fa(email, password, fullCode);
      saveSession({
        accessToken: response.access_token,
        refreshToken: response.refresh_token,
        role: response.role,
        tenantId: response.tenant_id,
        email: email,
      });
      toast.success("Autentificare reusita!");
      navigate(searchParams.get("redirect") || "/");
    } catch (err) {
      const msg = err.message || "Cod invalid";
      toast.error(msg);
      setCode(Array(CODE_LENGTH).fill(""));
      setFocusedIdx(0);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  }

  function handleOAuth(provider) {
    setLoginError("");
    const clientId = {
      google: "google-client-id-placeholder",
      github: "github-client-id-placeholder",
      linkedin: "linkedin-client-id-placeholder",
    }[provider];
    window.location.href = `/api/v1/auth/oauth/${provider}?client_id=${clientId}`;
  }

  if (pendingToken) {
    return (
      <div className="auth-shell">
        <div className="auth-card">
          <div className="auth-icon">
            <KeyRound size={28} strokeWidth={2} aria-hidden="true" />
          </div>
          <h1>Verificare in 2 pasi</h1>
          <p className="hint">Introdu codul din aplicatia de autentificare</p>
          <div className="code-grid" onPaste={handleCodePaste}>
            {code.map((digit, index) => (
              <input
                key={index}
                ref={(el) => (inputRefs.current[index] = el)}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleCodeChange(index, e.target.value)}
                onKeyDown={(e) => handleCodeKeyDown(index, e)}
                onFocus={() => setFocusedIdx(index)}
                className={[
                  focusedIdx === index ? "active" : "",
                  digit ? "has-value" : "",
                ].filter(Boolean).join(" ")}
                aria-label={`Cifra ${index + 1}`}
              />
            ))}
          </div>
          <p className="hint" style={{ marginTop: "0.7rem", fontSize: "0.8rem" }}>
            Codul se trimite automat
          </p>
          <button
            type="button"
            className="ghost-button"
            onClick={() => { setPendingToken(null); setCode(Array(CODE_LENGTH).fill("")); setLoginError(""); }}
            style={{ marginTop: "0.8rem" }}
          >
            Inapoi la login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-icon">
          <Shield size={28} strokeWidth={2} aria-hidden="true" />
        </div>
        <h1>Guardian</h1>
        <p className="hint" style={{ textAlign: "center", marginBottom: "1.5rem" }}>
          Platforma de securitate cibernetica
        </p>

        <form onSubmit={handleLogin} className="form-grid">
          <label>
            Email
            <input
              type="email"
              placeholder="nume@exemplu.ro"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setLoginError(""); }}
              autoComplete="email"
              required
              disabled={loading}
            />
          </label>

          <label>
            Parola
            <div className="password-field">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Parola ta"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setLoginError(""); }}
                autoComplete="current-password"
                required
                disabled={loading}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                aria-label={showPassword ? "Ascunde parola" : "Afiseaza parola"}
              >
                {showPassword ? <EyeOff size={16} strokeWidth={2} /> : <Eye size={16} strokeWidth={2} />}
              </button>
            </div>
          </label>

          {loginError && (
            <p className="error-text" style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <Lock size={14} strokeWidth={2} aria-hidden="true" />
              <span>{loginError}</span>
            </p>
          )}

          <button type="submit" disabled={loading} className="auth-submit">
            {loading ? "Se proceseaza..." : "Intra in cont"}
          </button>
        </form>

        <div className="auth-divider">
          <span>sau</span>
        </div>

        <div className="oauth-list">
          {["google", "github", "linkedin"].map((provider) => {
            const Icon = providerIcons?.[provider];
            return (
              <button
                key={provider}
                type="button"
                onClick={() => handleOAuth(provider)}
                disabled={loading}
                className="oauth-button"
              >
                {Icon && <Icon aria-hidden="true" />}
                <span style={{ textTransform: "capitalize" }}>{provider}</span>
              </button>
            );
          })}
        </div>

        <p className="auth-footer">
          Nu ai cont? <a href="/register">Inregistreaza-te</a>
        </p>
      </div>
    </div>
  );
}

export { LoginPage };
export default LoginPage;
