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
    // API returns paginated: { items: [...], next_cursor: "..." }
    const items = Array.isArray(data) ? data : (data?.items || []);
    setCachedValue(FINDINGS_CACHE_KEY, items, 15000);
    return items;
  },

  async remove(findingId) {
    const data = await apiAuthRequest(`/findings/${findingId}`, { method: "DELETE" });
    invalidateCache([FINDINGS_CACHE_KEY, "alerts:list"]);
    return data;
  },

  async resolve(findingId) {
    const data = await apiAuthRequest(`/findings/${findingId}/resolve`, { method: "POST" });
    invalidateCache([FINDINGS_CACHE_KEY, "alerts:list"]);
    return data;
  },
};

