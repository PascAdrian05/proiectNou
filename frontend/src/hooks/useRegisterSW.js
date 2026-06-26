import { useEffect } from "react";

export function useRegisterSW() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    let cancelled = false;

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
        console.warn("[SW] Registration failed (expected in dev)");
      }
    }

    register();
    return () => { cancelled = true; };
  }, []);
}
