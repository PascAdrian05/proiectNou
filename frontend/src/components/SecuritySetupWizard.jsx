import { useState, useEffect } from "react";
import { authService } from "../services/api/authService";
import TOTPSetup from "./TOTPSetup";

const STEPS = [
  { id: "passkey", title: "Add a Passkey", description: "Fast, phishing-resistant login with fingerprint or face ID" },
  { id: "backup", title: "Generate Backup Codes", description: "One-click recovery if you lose access to your authenticator" },
  { id: "2fa", title: "Enable Two-Factor Auth", description: "Extra layer of security with your authenticator app" },
];

export default function SecuritySetupWizard({ onComplete, onSkip }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [backupCodes, setBackupCodes] = useState(null);
  const [loading, setLoading] = useState({});
  const [error, setError] = useState("");

  // Step 1: Passkey - Not implemented yet, placeholder
  // Step 2: Generate backup codes
  // Step 3: TOTP 2FA

  async function handleGenerateBackupCodes() {
    setLoading((prev) => ({ ...prev, backup: true }));
    setError("");
    try {
      const result = await authService.generateBackupCodes();
      setBackupCodes(result.codes);
    } catch (err) {
      setError(err.message || "Failed to generate backup codes");
    } finally {
      setLoading((prev) => ({ ...prev, backup: false }));
    }
  }

  function handleDownloadBackupCodes() {
    if (!backupCodes) return;
    const content = backupCodes.join("\n");
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "security-monitor-backup-codes.txt";
    a.click();
    URL.revokeObjectURL(url);
    goNext();
  }

  function goNext() {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      handleFinish();
    }
  }

  function goBack() {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  }

  async function handleFinish() {
    try {
      await authService.markSecuritySetupCompleted();
      onComplete();
    } catch {
      // Non-critical, continue
      onComplete();
    }
  }

  function renderStep() {
    switch (STEPS[currentStep].id) {
      case "passkey":
        return (
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/30">
              <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
            </div>
            <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
              Passkeys let you sign in with your device's biometrics (fingerprint, face ID) or PIN. No passwords needed.
            </p>
            <p className="mb-6 text-xs text-gray-400 dark:text-gray-500">
              Coming soon in a future update.
            </p>
            <button
              onClick={goNext}
              className="rounded-md bg-indigo-600 px-6 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Skip for now
            </button>
          </div>
        );

      case "backup":
        if (backupCodes) {
          return (
            <div>
              <div className="mb-4 rounded-md bg-amber-50 p-4 dark:bg-amber-900/20">
                <h3 className="text-sm font-medium text-amber-800 dark:text-amber-300">
                  Save these codes!
                </h3>
                <p className="mt-1 text-xs text-amber-700 dark:text-amber-400">
                  Each code can only be used once. Store them in a password manager or print them.
                </p>
              </div>
              <div className="mb-4 grid grid-cols-2 gap-2">
                {backupCodes.map((code, i) => (
                  <code
                    key={i}
                    className="rounded bg-gray-100 px-3 py-2 text-center font-mono text-sm dark:bg-gray-700"
                  >
                    {code}
                  </code>
                ))}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={goBack}
                  className="flex-1 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
                >
                  Back
                </button>
                <button
                  onClick={handleDownloadBackupCodes}
                  className="flex-1 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  Download & Continue
                </button>
              </div>
            </div>
          );
        }

        return (
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
              <svg className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">
              Generate 10 one-time backup codes. Keep them safe — they're your lifeline if you lose your authenticator app.
            </p>
            <button
              onClick={handleGenerateBackupCodes}
              disabled={loading.backup}
              className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading.backup ? "Generating..." : "Generate Backup Codes"}
            </button>
          </div>
        );

      case "2fa":
        return (
          <TOTPSetup onComplete={goNext} />
        );

      default:
        return null;
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            {STEPS.map((step, i) => (
              <div key={step.id} className="flex items-center">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium ${
                    i <= currentStep
                      ? "bg-indigo-600 text-white"
                      : "bg-gray-200 text-gray-500 dark:bg-gray-700"
                  }`}
                >
                  {i + 1}
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={`mx-2 h-0.5 w-12 ${
                      i < currentStep ? "bg-indigo-600" : "bg-gray-200 dark:bg-gray-700"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="mt-2 flex justify-between text-xs text-gray-400">
            <span>Passkey</span>
            <span>Backup</span>
            <span>2FA</span>
          </div>
        </div>

        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
          {STEPS[currentStep].title}
        </h2>
        <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">
          {STEPS[currentStep].description}
        </p>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">
            {error}
          </div>
        )}

        {renderStep()}

        <div className="mt-4 text-center">
          <button
            onClick={onSkip}
            className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            Skip all — remind me later
          </button>
        </div>
      </div>
    </div>
  );
}