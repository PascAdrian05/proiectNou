import { apiAuthRequest } from "./client";
import { getCachedValue, invalidateCache, setCachedValue } from "./cache";

const SCAN_RUNS_CACHE_KEY = "scans:runs";

export const scansService = {
  async listRuns(forceRefresh = false) {
    const cached = !forceRefresh ? getCachedValue(SCAN_RUNS_CACHE_KEY) : null;
    if (cached) {
      return cached;
    }

    const data = await apiAuthRequest("/scans/runs", { method: "GET" });
    setCachedValue(SCAN_RUNS_CACHE_KEY, data, 12000);
    return data;
  },

  async enqueue(payload) {
    // TODO: Bind your API data here if backend payload fields change.
    const data = await apiAuthRequest("/scans/enqueue", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    invalidateCache([SCAN_RUNS_CACHE_KEY, "findings:list", "alerts:list"]);
    return data;
  },

  async remove(scanRunId) {
    const data = await apiAuthRequest(`/scans/${scanRunId}`, {
      method: "DELETE",
    });
    invalidateCache([SCAN_RUNS_CACHE_KEY, "findings:list", "alerts:list"]);
    return data;
  },

  async removeAll() {
    const data = await apiAuthRequest("/scans/history", {
      method: "DELETE",
    });
    invalidateCache([SCAN_RUNS_CACHE_KEY, "findings:list", "alerts:list"]);
    return data;
  },
};
