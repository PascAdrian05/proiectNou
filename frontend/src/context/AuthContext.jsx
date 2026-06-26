import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { storage } from "../services/storage";
import { presenceService } from "../services/api/presenceService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState({}); // Start with empty auth to force login

  useEffect(() => {
    // Clear any existing session on app load to force login
    storage.clearAuthSession();
    
    if (!auth.accessToken) {
      return undefined;
    }

    let isMounted = true;

    async function sendHeartbeat() {
      try {
        await presenceService.heartbeat();
      } catch {
        // presence is best-effort
      }
    }

    sendHeartbeat();
    const intervalId = window.setInterval(sendHeartbeat, 30000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
      if (!isMounted) {
        return;
      }
    };
  }, [auth.accessToken]);

  const value = useMemo(() => {
    const isAuthenticated = Boolean(auth.accessToken);

    function saveSession(nextSession) {
      storage.setAuthSession(nextSession);
      setAuth(nextSession);
    }

    function clearSession() {
      storage.clearAuthSession();
      setAuth(storage.getAuthSession());
    }

    return {
      auth,
      isAuthenticated,
      saveSession,
      clearSession,
    };
  }, [auth]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
