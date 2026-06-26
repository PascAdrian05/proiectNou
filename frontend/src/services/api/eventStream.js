function getAccessToken() {
  try {
    const raw = localStorage.getItem("security_monitor_auth");
    if (!raw) return null;
    return JSON.parse(raw).accessToken;
  } catch {
    return null;
  }
}

export function createEventSource(url, options = {}) {
  const urlWithToken = new URL(url, window.location.origin);
  const token = options.session?.accessToken || getAccessToken();
  if (token) urlWithToken.searchParams.append("token", token);
  return new EventSource(urlWithToken.toString());
}

export function subscribeToScanEvents(eventHandlers) {
  const source = createEventSource("/api/v1/events/scans/stream", {
    session: { accessToken: getAccessToken() },
  });

  source.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);

      // Handle AI analysis completed events (from Redis pub/sub via SSE)
      if (payload?.type === "ai_analysis_completed") {
        if (eventHandlers.onCompleted) {
          eventHandlers.onCompleted({
            type: "ai_analysis_completed",
            scan_run_id: payload.scan_run_id,
            findings_analyzed: payload.findings_analyzed,
          });
        }
        return;
      }

      // Handle scan progress/completed events (from Redis pub/sub via SSE)
      if (payload?.type === "scan_progress" || payload?.type === "scan_completed") {
        if (payload.type === "scan_progress" && eventHandlers.onProgress) {
          eventHandlers.onProgress({
            type: "scan_progress",
            scan_run_id: payload.scan_run_id,
            step: payload.step,
            status: payload.status,
            progress: payload.progress,
          });
        } else if (payload.type === "scan_completed" && eventHandlers.onCompleted) {
          eventHandlers.onCompleted({
            type: "scan_completed",
            scan_run_id: payload.scan_run_id,
            status: payload.status,
          });
        }
        return;
      }

      // Handle DB poll snapshot (has "runs" array)
      if (payload?.runs) {
        for (const run of payload.runs) {
          if (run.status === "running" || run.status === "pending") {
            const progress = run.progress ? JSON.parse(run.progress) : null;
            if (eventHandlers.onProgress) {
              eventHandlers.onProgress({
                type: "scan_progress",
                scan_run_id: run.id,
                step: run.current_step,
                status: run.status,
                progress,
              });
            }
          } else if (run.status === "completed" || run.status === "failed") {
            if (eventHandlers.onCompleted) {
              eventHandlers.onCompleted({
                type: "scan_completed",
                scan_run_id: run.id,
                status: run.status,
              });
            }
          }
        }
      }
    } catch {}
  };

  source.onerror = () => source.close();

  return () => source.close();
}
