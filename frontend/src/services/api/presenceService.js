import { apiAuthRequest } from "./client";

export const presenceService = {
  async heartbeat() {
    return apiAuthRequest("/presence/heartbeat", { method: "POST" });
  },

  async online() {
    return apiAuthRequest("/presence/online", { method: "GET" });
  },
};
