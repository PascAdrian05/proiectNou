import { apiAuthRequest, apiRequest } from "./client";

export const passkeyService = {
  /**
   * Begin passkey registration — get options for navigator.credentials.create().
   */
  async beginRegistration() {
    return apiAuthRequest("/auth/passkey/register/begin", {
      method: "POST",
    });
  },

  /**
   * Complete passkey registration after user creates a credential.
   */
  async completeRegistration(credential, challengeId) {
    return apiAuthRequest("/auth/passkey/register/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential, challenge_id: challengeId }),
    });
  },

  /**
   * Begin passkey authentication — get options for navigator.credentials.get().
   */
  async beginAuthentication(email) {
    return apiRequest("/auth/passkey/login/begin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email || null }),
    });
  },

  /**
   * Complete passkey authentication after user selects a credential.
   */
  async completeAuthentication(credential, challengeId, email) {
    return apiRequest("/auth/passkey/login/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential, challenge_id: challengeId, email: email || null }),
    });
  },

  /**
   * List all passkey credentials for the current user.
   */
  async listCredentials() {
    return apiAuthRequest("/auth/passkey/credentials", {
      method: "GET",
    });
  },

  /**
   * Delete a passkey credential.
   */
  async deleteCredential(credentialId) {
    return apiAuthRequest(`/auth/passkey/credentials/${credentialId}`, {
      method: "DELETE",
    });
  },
};