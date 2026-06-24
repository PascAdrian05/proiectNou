import { apiAuthRequest } from "./client";

export const behaviorService = {
  async sendEvents(events) {
    if (!events.length) {
      return { stored_events: 0 };
    }

    return apiAuthRequest("/behavior/events", {
      method: "POST",
      body: JSON.stringify({ events }),
    });
  },

  async getScore() {
    return apiAuthRequest("/behavior/score", { method: "GET" });
  },
};
