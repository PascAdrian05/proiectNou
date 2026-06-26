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

  async getLimits() {
    const data = await apiAuthRequest("/scans/limits", { method: "GET" });
    return data;
  },

  async enqueue(payload) {
    try {
      const data = await apiAuthRequest("/scans/enqueue", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      invalidateCache([SCAN_RUNS_CACHE_KEY, "findings:list", "alerts:list"]);
      return data;
    } catch (error) {
      console.error("Failed to enqueue scan:", error);
      throw error;
    }
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
