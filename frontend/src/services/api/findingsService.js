import { apiAuthRequest } from "./client";
import { getCachedValue, invalidateCache, setCachedValue } from "./cache";

const FINDINGS_CACHE_KEY = "findings:list";

export const findingsService = {
  async list(forceRefresh = false) {
    const cached = !forceRefresh ? getCachedValue(FINDINGS_CACHE_KEY) : null;
    if (cached) {
      return cached;
    }

    const data = await apiAuthRequest("/findings", { method: "GET" });
    setCachedValue(FINDINGS_CACHE_KEY, data, 15000);
    return data;
  },

  async remove(findingId) {
    const data = await apiAuthRequest(`/findings/${findingId}`, { method: "DELETE" });
    invalidateCache([FINDINGS_CACHE_KEY, "alerts:list"]);
    return data;
  },
};
