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
    setCachedValue(ALERTS_CACHE_KEY, data, 15000);
    return data;
  },

  async remove(alertId) {
    const data = await apiAuthRequest(`/alerts/${alertId}`, { method: "DELETE" });
    invalidateCache([ALERTS_CACHE_KEY]);
    return data;
  },
};
