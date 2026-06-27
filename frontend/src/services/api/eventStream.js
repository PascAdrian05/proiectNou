/**
 * Server-Sent Events helpers.
 *
 * Authentication
 * --------------
 * ``EventSource`` cannot set custom headers, so we cannot send a Bearer
 * token in the way our other endpoints accept. Passing the long-lived
 * access JWT through a query string would leak it into proxy logs,
 * browser history and the ``Referer`` header on cross-page navigations.
 *
 * Instead the backend exposes a ticket flow: we POST with the bearer
 * token to ``/events/ticket`` and receive a 60-second, single-use UUID,
 * then open ``/events/{namespace}/stream?ticket=...``. This module
 * implements exactly that pattern.
 */

function getAccessToken() {
  try {
    const raw = localStorage.getItem("security_monitor_auth");
    if (!raw) return null;
    return JSON.parse(raw).accessToken;
  } catch {
    return null;
  }
}

function getApiBase() {
  if (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  return "/api/v1";
}

async function fetchWithAuth(path, options = {}) {
  const token = getAccessToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${getApiBase()}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${body || res.statusText}`);
  }
  return res.json();
}

/**
 * Trade the bearer access token for a single-use SSE ticket. The ticket
 * is consumed the moment the EventSource opens.
 */
export async function issueSseTicket() {
  const { ticket, expires_in } = await fetchWithAuth("/events/ticket", {
    method: "POST",
  });
  return { ticket, expiresIn: expires_in };
}

/**
 * Open an authenticated SSE stream for the given namespace
 * (``scans`` / ``alerts`` / ``findings``).
 */
export async function openAuthenticatedEventSource(namespace) {
  const { ticket } = await issueSseTicket();
  const url = new URL(`${getApiBase()}/events/${namespace}/stream`, window.location.origin);
  url.searchParams.set("ticket", ticket);
  return new EventSource(url.toString());
}

/**
 * Subscribe to scan events. Returns an unsubscribe function.
 */
export function subscribeToScanEvents(eventHandlers) {
  let source = null;
  let cancelled = false;

  (async () => {
    try {
      source = await openAuthenticatedEventSource("scans");
      if (cancelled) {
        source.close();
        return;
      }

      source.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);

          if (payload?.type === "ai_analysis_completed") {
            eventHandlers.onCompleted?.({
              type: "ai_analysis_completed",
              scan_run_id: payload.scan_run_id,
              findings_analyzed: payload.findings_analyzed,
            });
            return;
          }

          if (payload?.type === "scan_progress") {
            eventHandlers.onProgress?.({
              type: "scan_progress",
              scan_run_id: payload.scan_run_id,
              step: payload.step,
              status: payload.status,
              progress: payload.progress,
            });
            return;
          }

          if (payload?.type === "scan_completed") {
            eventHandlers.onCompleted?.({
              type: "scan_completed",
              scan_run_id: payload.scan_run_id,
              status: payload.status,
            });
            return;
          }

          if (payload?.runs) {
            for (const run of payload.runs) {
              if (run.status === "running" || run.status === "pending") {
                const progress = run.progress ? JSON.parse(run.progress) : null;
                eventHandlers.onProgress?.({
                  type: "scan_progress",
                  scan_run_id: run.id,
                  step: run.current_step,
                  status: run.status,
                  progress,
                });
              } else if (run.status === "completed" || run.status === "failed") {
                eventHandlers.onCompleted?.({
                  type: "scan_completed",
                  scan_run_id: run.id,
                  status: run.status,
                });
              }
            }
          }
        } catch {
          // Ignore malformed payloads — the stream stays open.
        }
      };

      source.onerror = (err) => {
        // EventSource auto-retries, so just bubble for visibility.
        eventHandlers.onError?.(err);
      };
    } catch (err) {
      eventHandlers.onError?.(err);
    }
  })();

  return () => {
    cancelled = true;
    if (source) {
      try {
        source.close();
      } catch {
        /* ignore */
      }
    }
  };
}