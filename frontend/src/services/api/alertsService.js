import { apiAuthRequest } from "./client";
import { getCachedValue, invalidateCache, setCachedValue } from "./cache";

const ALERTS_CACHE_KEY = "alerts:list";

export const alertsService = {
  async list() {
    const cached = getCachedValue(ALERTS_CACHE_KEY);
    if (cached) {
      return cached;
    }

    const data = await apiAuthRequest("/alerts", { method: "GET" });
    // API returns paginated: { items: [...], next_cursor: "..." }
    const items = Array.isArray(data) ? data : (data?.items || []);
    setCachedValue(ALERTS_CACHE_KEY, items, 15000);
    return items;
  },

  async remove(alertId) {
    const data = await apiAuthRequest(`/alerts/${alertId}`, { method: "DELETE" });
    invalidateCache([ALERTS_CACHE_KEY]);
    return data;
  },
};

