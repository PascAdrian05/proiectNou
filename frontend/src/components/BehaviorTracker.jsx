import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { behaviorService } from "../services/api/behaviorService";

export function BehaviorTracker() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  const queueRef = useRef([]);
  const flushTimerRef = useRef(null);
  const flushInFlightRef = useRef(false);

  useEffect(() => {
    if (!isAuthenticated) {
      return undefined;
    }

    function pushEvent(type, meta = {}) {
      queueRef.current.push({
        type,
        path: location.pathname,
        timestamp: new Date().toISOString(),
        meta,
      });
    }

    function handleClick(event) {
      const target = event.target;
      pushEvent("click", {
        tag: target?.tagName || "unknown",
        role: target?.getAttribute?.("role") || "",
      });
    }

    function handleKeydown(event) {
      pushEvent("keydown", {
        key: event.key,
      });
    }

    function handleSubmit(event) {
      const form = event.target;
      pushEvent("submit", {
        name: form?.getAttribute?.("name") || form?.tagName || "form",
      });
    }

    function handleVisibilityChange() {
      pushEvent(document.hidden ? "visibility_hidden" : "visibility_visible");
    }

    function handleBlur() {
      pushEvent("blur");
    }

    function handleFocus() {
      pushEvent("focus");
    }

    document.addEventListener("click", handleClick, true);
    document.addEventListener("keydown", handleKeydown, true);
    document.addEventListener("submit", handleSubmit, true);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleBlur);
    window.addEventListener("focus", handleFocus);

    flushTimerRef.current = window.setInterval(async () => {
      if (flushInFlightRef.current || queueRef.current.length === 0) {
        return;
      }

      const events = queueRef.current.splice(0, queueRef.current.length);
      flushInFlightRef.current = true;
      try {
        await behaviorService.sendEvents(events);
      } catch {
        queueRef.current.unshift(...events);
      } finally {
        flushInFlightRef.current = false;
      }
    }, 5000);

    pushEvent("page_view", { path: location.pathname });

    return () => {
      document.removeEventListener("click", handleClick, true);
      document.removeEventListener("keydown", handleKeydown, true);
      document.removeEventListener("submit", handleSubmit, true);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("blur", handleBlur);
      window.removeEventListener("focus", handleFocus);
      if (flushTimerRef.current) {
        window.clearInterval(flushTimerRef.current);
      }
    };
  }, [isAuthenticated, location.pathname]);

  useEffect(() => {
    if (!isAuthenticated) {
      return undefined;
    }

    queueRef.current.push({
      type: "route_change",
      path: location.pathname,
      timestamp: new Date().toISOString(),
      meta: {},
    });
  }, [isAuthenticated, location.pathname]);

  return null;
}
