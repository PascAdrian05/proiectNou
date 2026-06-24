const AUTH_STORAGE_KEY = "security_monitor_auth";

export const storage = {
  getAuthSession() {
    try {
      const raw = localStorage.getItem(AUTH_STORAGE_KEY);
      if (!raw) {
        return { accessToken: "", refreshToken: "", role: "", tenantId: "" };
      }
      return JSON.parse(raw);
    } catch {
      return { accessToken: "", refreshToken: "", role: "", tenantId: "" };
    }
  },

  setAuthSession(session) {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
  },

  clearAuthSession() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  },
};
