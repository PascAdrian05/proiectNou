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

  // 2FA state
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
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-base-300 via-base-200 to-base-300">
        <div className="card w-full max-w-md bg-base-100 shadow-2xl">
          <div className="card-body items-center text-center p-8">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <KeyRound className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-2xl font-bold">Verificare in 2 pasi</h2>
            <p className="text-base-content/60 mt-1">
              Introdu codul din aplicatia de autentificare
            </p>
            <div className="flex gap-3 mt-6" onPaste={handleCodePaste}>
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
                  className={`w-12 h-14 text-center text-2xl font-bold rounded-lg border-2 bg-base-200 transition-all duration-150 outline-none
                    ${focusedIdx === index ? "border-primary ring-2 ring-primary/30 scale-105" : "border-base-300"}
                    ${code[index] ? "border-primary" : ""}`}
                />
              ))}
            </div>
            <p className="text-xs text-base-content/40 mt-4">Codul se trimite automat</p>
            <button
              onClick={() => { setPendingToken(null); setCode(Array(CODE_LENGTH).fill("")); setLoginError(""); }}
              className="btn btn-ghost btn-sm mt-4"
            >
              Inapoi la login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-base-300 via-base-200 to-base-300 p-4">
      <div className="card w-full max-w-md bg-base-100 shadow-2xl">
        <div className="card-body p-8">
          <div className="text-center mb-6">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <Shield className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-3xl font-bold">Guardian</h1>
            <p className="text-base-content/60 mt-1">Platforma de securitate cibernetica</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <label className="form-control">
              <div className="label">
                <span className="label-text">Email</span>
              </div>
              <input
                type="email"
                placeholder="nume@exemplu.ro"
                className="input input-bordered w-full"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setLoginError(""); }}
                autoComplete="email"
                required
                disabled={loading}
              />
            </label>

            <label className="form-control">
              <div className="label">
                <span className="label-text">Parola</span>
              </div>
              <div className="join w-full">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Parola ta"
                  className="input input-bordered join-item w-full"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setLoginError(""); }}
                  autoComplete="current-password"
                  required
                  disabled={loading}
                />
                <button
                  type="button"
                  className="btn btn-square join-item btn-outline"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </label>

            {loginError && (
              <div className="alert alert-error text-sm p-3">
                <Lock className="w-4 h-4 shrink-0" />
                <span>{loginError}</span>
              </div>
            )}

            <button type="submit" className="btn btn-primary w-full" disabled={loading}>
              {loading ? <span className="loading loading-spinner" /> : null}
              {loading ? "Se proceseaza..." : "Intra in cont"}
            </button>
          </form>

          <div className="divider my-6 text-xs text-base-content/40">sau</div>

          <div className="space-y-2">
            {["google", "github", "linkedin"].map((provider) => {
              const Icon = providerIcons?.[provider];
              return (
                <button
                  key={provider}
                  onClick={() => handleOAuth(provider)}
                  disabled={loading}
                  className="btn btn-outline w-full gap-3"
                >
                  {Icon && <Icon className="w-5 h-5" />}
                  <span className="capitalize">{provider}</span>
                </button>
              );
            })}
          </div>

          <p className="text-center text-sm text-base-content/40 mt-6">
            Nu ai cont?{" "}
            <a href="/register" className="link link-primary">
              Inregistreaza-te
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

export { LoginPage };
export default LoginPage;
