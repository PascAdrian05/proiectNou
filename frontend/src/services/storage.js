const AUTH_STORAGE_KEY = "security_monitor_auth";
const USER_DATA_KEY = "security_monitor_user_data";

const EMPTY_SESSION = Object.freeze({
  accessToken: "",
  refreshToken: "",
  role: "",
  tenantId: "",
  stepUpToken: "",
});

function safeRemove(...keys) {
  for (const key of keys) {
    try {
      localStorage.removeItem(key);
    } catch {
      /* localStorage may be unavailable (private mode, SSR, sandboxed iframe) */
    }
  }
}

export const storage = {
  getAuthSession() {
    let raw;
    try {
      raw = localStorage.getItem(AUTH_STORAGE_KEY);
    } catch {
      return { ...EMPTY_SESSION };
    }

    if (!raw) {
      return { ...EMPTY_SESSION };
    }

    let session;
    try {
      session = JSON.parse(raw);
    } catch {
      // Corrupt storage — wipe and return empty session.
      safeRemove(AUTH_STORAGE_KEY, USER_DATA_KEY);
      return { ...EMPTY_SESSION };
    }

    if (!session.accessToken || !session.refreshToken) {
      safeRemove(AUTH_STORAGE_KEY, USER_DATA_KEY);
      return { ...EMPTY_SESSION };
    }

    return { ...EMPTY_SESSION, ...session };
  },

  setAuthSession(session) {
    if (!session || !session.accessToken || !session.refreshToken) {
      return;
    }
    try {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
    } catch (error) {
      console.error("Error saving auth session:", error);
    }
  },

  clearAuthSession() {
    safeRemove(AUTH_STORAGE_KEY, USER_DATA_KEY);
  },

  setUserData(key, value) {
    const existing = storage.getUserData() || {};
    existing[key] = value;
    try {
      localStorage.setItem(USER_DATA_KEY, JSON.stringify(existing));
    } catch (error) {
      console.error("Error saving user data:", error);
    }
  },

  getUserData(key = null) {
    let raw;
    try {
      raw = localStorage.getItem(USER_DATA_KEY);
    } catch {
      return null;
    }
    if (!raw) return null;

    try {
      const data = JSON.parse(raw);
      return key ? data[key] : data;
    } catch (error) {
      console.error("Error reading user data:", error);
      return null;
    }
  },
};