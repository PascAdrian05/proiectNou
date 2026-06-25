import { useState, useEffect } from "react";
import { startRegistration } from "@simplewebauthn/browser";
import { passkeyService } from "../services/api/passkeyService";

export default function PasskeyManager() {
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadCredentials();
  }, []);

  async function loadCredentials() {
    setLoading(true);
    try {
      const result = await passkeyService.listCredentials();
      setCredentials(result.credentials || []);
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister() {
    setRegistering(true);
    setError("");

    try {
      // Step 1: Get registration options from server
      const { publicKey, challenge_id } = await passkeyService.beginRegistration();

      // Step 2: Create credential via browser WebAuthn API
      const credential = await startRegistration({ optionsJSON: publicKey });

      // Step 3: Send credential to server for verification
      await passkeyService.completeRegistration(credential, challenge_id);

      // Reload credentials list
      await loadCredentials();
    } catch (err) {
      if (err.name === "NotAllowedError") {
        setError("Passkey registration was cancelled.");
      } else if (err.name === "InvalidStateError") {
        setError("This passkey has already been registered.");
      } else {
        setError(err.message || "Failed to register passkey");
      }
    } finally {
      setRegistering(false);
    }
  }

  async function handleDelete(credentialId) {
    if (!confirm("Remove this passkey? You may need to re-register to use it again.")) return;

    try {
      await passkeyService.deleteCredential(credentialId);
      await loadCredentials();
    } catch (err) {
      setError(err.message || "Failed to delete passkey");
    }
  }

  return (
    <div className="settings-section">
      <h3>Passkeys</h3>
      <p className="hint">
        Passkeys let you sign in with your device's biometrics (fingerprint, face ID) or PIN.
        They're more secure than passwords and resistant to phishing.
      </p>

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400 mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-gray-400">Loading credentials...</p>
      ) : credentials.length > 0 ? (
        <div className="space-y-2 mb-4">
          {credentials.map((cred) => (
            <div
              key={cred.id}
              className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800"
            >
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {cred.device_name || "Passkey"}
                </p>
                <p className="text-xs text-gray-500">
                  Added {new Date(cred.created_at).toLocaleDateString()}
                  {cred.last_used_at && ` · Last used ${new Date(cred.last_used_at).toLocaleDateString()}`}
                </p>
              </div>
              <button
                type="button"
                className="text-sm text-red-600 hover:text-red-800 dark:text-red-400"
                onClick={() => handleDelete(cred.id)}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500 mb-4">
          No passkeys registered yet. Add one for faster, more secure sign-in.
        </p>
      )}

      <button
        type="button"
        onClick={handleRegister}
        disabled={registering}
        className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {registering ? "Registering..." : "Add a Passkey"}
      </button>
    </div>
  );
}