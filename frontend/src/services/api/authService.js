import { apiAuthRequest, apiRequest } from "./client";
import { storage } from "../storage";

export const authService = {
  /**
   * Login with email and password.
   * Returns { access_token, refresh_token, requires_2fa, ... }
   */
  async login(email, password) {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const result = await apiRequest("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });

    return result;
  },

  /**
   * Verify 2FA token during login.
   */
  async verify2fa(email, password, token) {
    const result = await apiRequest("/auth/2fa/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, token }),
    });

    return result;
  },

  /**
   * Register a new account.
   */
  async register(tenantName, email, password) {
    return apiRequest("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tenant_name: tenantName,
        email,
        password,
      }),
    });
  },

  /**
   * Refresh the session.
   */
  async refresh(refreshToken) {
    return apiRequest("/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  /**
   * Logout.
   */
  async logout(refreshToken) {
    try {
      await apiRequest("/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      // Best-effort
    }
  },

  // === 2FA ===

  /**
   * Initiate 2FA setup (get QR code).
   */
  async setup2fa(password) {
    return apiAuthRequest("/auth/2fa/setup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
  },

  /**
   * Enable 2FA after verifying a token.
   */
  async enable2fa(secret, token) {
    return apiAuthRequest("/auth/2fa/enable", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ secret, token }),
    });
  },

  /**
   * Disable 2FA.
   */
  async disable2fa(password) {
    return apiAuthRequest("/auth/2fa/disable", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
  },

  // === Backup Codes ===

  /**
   * Generate backup codes.
   */
  async generateBackupCodes() {
    return apiAuthRequest("/auth/2fa/backup-codes", {
      method: "POST",
    });
  },

  /**
   * Recover account with a backup code.
   */
  async recoverWithBackupCode(email, password, code) {
    return apiRequest("/auth/2fa/recover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, code }),
    });
  },

  // === Step-Up Authentication ===

  /**
   * Perform step-up authentication for sensitive actions.
   */
  async stepUp(token) {
    return apiAuthRequest("/auth/step-up", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
  },

  // === Security Status ===

  /**
   * Get the current security status and score.
   */
  async getSecurityStatus() {
    return apiAuthRequest("/auth/security-status", {
      method: "GET",
    });
  },

  /**
   * Mark the security onboarding wizard as completed.
   */
  async markSecuritySetupCompleted() {
    return apiAuthRequest("/auth/security-setup-completed", {
      method: "POST",
    });
  },
};