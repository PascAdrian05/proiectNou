import { apiAuthRequest } from "./client";

export const tenantService = {
  async getSettings() {
    return apiAuthRequest("/tenant/settings", { method: "GET" });
  },

  async updateSettings(payload) {
    return apiAuthRequest("/tenant/settings", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async sendTestAlert() {
    return apiAuthRequest("/tenant/settings/test-alert", {
      method: "POST",
    });
  },
};
