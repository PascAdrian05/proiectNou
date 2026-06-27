import { useEffect, useRef } from "react";

export function useRegisterSW() {
  const registeredRef = useRef(false);

  useEffect(() => {
    // Prevent double-registration in dev StrictMode
    if (registeredRef.current) return;

    if (!("serviceWorker" in navigator)) return;

    let cancelled = false;
    registeredRef.current = true;

    async function register() {
      try {
        const reg = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
        if (cancelled) return;

        reg.addEventListener("updatefound", () => {
          const newWorker = reg.installing;
          if (!newWorker) return;
          newWorker.addEventListener("statechange", () => {
            if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
              console.log("[SW] New version available — refresh to update");
            }
          });
        });
      } catch {
        // Silently ignore — SW registration is best-effort
      }
    }

    register();
    return () => { cancelled = true; };
  }, []);
}

