import { apiAuthRequest } from "./client";
import { getCachedValue, invalidateCache, setCachedValue } from "./cache";

const WEBSITES_CACHE_KEY = "websites:list";

export const websitesService = {
  async list() {
    const cached = getCachedValue(WEBSITES_CACHE_KEY);
    if (cached) {
      return cached;
    }

    const data = await apiAuthRequest("/websites", { method: "GET" });
    setCachedValue(WEBSITES_CACHE_KEY, data, 20000);
    return data;
  },

  async create(payload) {
    // TODO: Bind your API data here if backend payload fields change.
    const data = await apiAuthRequest("/websites", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    invalidateCache([WEBSITES_CACHE_KEY]);
    return data;
  },

  async remove(websiteId) {
    const data = await apiAuthRequest(`/websites/${websiteId}`, {
      method: "DELETE",
    });
    invalidateCache([WEBSITES_CACHE_KEY, "scans:runs", "findings:list", "alerts:list"]);
    return data;
  },
};
