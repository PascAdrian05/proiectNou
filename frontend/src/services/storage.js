const AUTH_STORAGE_KEY = "security_monitor_auth";
const USER_DATA_KEY = "security_monitor_user_data";

export const storage = {
  getAuthSession() {
    try {
      const raw = localStorage.getItem(AUTH_STORAGE_KEY);
      if (!raw) {
        return { accessToken: "", refreshToken: "", role: "", tenantId: "" };
      }
      const session = JSON.parse(raw);
      // Validate session has required fields
      if (!session.accessToken || !session.refreshToken) {
        this.clearAuthSession();
        return { accessToken: "", refreshToken: "", role: "", tenantId: "" };
      }
      return session;
    } catch (error) {
      console.error("Error reading auth session:", error);
      this.clearAuthSession();
      return { accessToken: "", refreshToken: "", role: "", tenantId: "" };
    }
  },

  setAuthSession(session) {
    try {
      if (session && session.accessToken && session.refreshToken) {
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
      }
    } catch (error) {
      console.error("Error saving auth session:", error);
    }
  },

  clearAuthSession() {
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      localStorage.removeItem(USER_DATA_KEY);
    } catch (error) {
      console.error("Error clearing auth session:", error);
    }
  },

  // Additional methods for user data persistence
  setUserData(key, value) {
    try {
      const existing = this.getUserData() || {};
      existing[key] = value;
      localStorage.setItem(USER_DATA_KEY, JSON.stringify(existing));
    } catch (error) {
      console.error("Error saving user data:", error);
    }
  },

  getUserData(key = null) {
    try {
      const raw = localStorage.getItem(USER_DATA_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      return key ? data[key] : data;
    } catch (error) {
      console.error("Error reading user data:", error);
      return null;
    }
  },
};
