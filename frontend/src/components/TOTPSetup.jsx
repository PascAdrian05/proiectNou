import { useState } from "react";
import { authService } from "../services/api/authService";

export default function TOTPSetup({ onComplete }) {
  const [step, setStep] = useState("password"); // password, qr, done
  const [password, setPassword] = useState("");
  const [secret, setSecret] = useState("");
  const [qrCode, setQrCode] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handlePasswordSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await authService.setup2fa(password);
      setSecret(result.secret);
      setQrCode(result.qr_code);
      setStep("qr");
    } catch (err) {
      setError(err.message || "Failed to start 2FA setup");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifySubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await authService.enable2fa(secret, token);
      setStep("done");
      if (onComplete) onComplete();
    } catch (err) {
      setError(err.message || "Invalid code. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (step === "password") {
    return (
      <form onSubmit={handlePasswordSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Enter your password to begin
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            required
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading || !password}
          className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Starting..." : "Continue"}
        </button>
      </form>
    );
  }

  if (step === "qr") {
    return (
      <form onSubmit={handleVerifySubmit} className="space-y-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.):
        </p>
        {qrCode && (
          <div className="flex justify-center">
            <img src={qrCode} alt="2FA QR Code" className="h-40 w-40" />
          </div>
        )}
        <p className="text-xs text-gray-400 break-all">
          Or enter manually: <code className="text-indigo-600">{secret}</code>
        </p>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Verification Code
          </label>
          <input
            type="text"
            inputMode="numeric"
            pattern="[0-9]{6}"
            maxLength={6}
            value={token}
            onChange={(e) => setToken(e.target.value.replace(/\D/g, "").slice(0, 6))}
            placeholder="000000"
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-center text-2xl tracking-widest shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            required
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading || token.length !== 6}
          className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Verifying..." : "Enable 2FA"}
        </button>
      </form>
    );
  }

  return (
    <div className="text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
        <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <p className="text-sm font-medium text-green-700 dark:text-green-400">
        2FA enabled successfully!
      </p>
    </div>
  );
}