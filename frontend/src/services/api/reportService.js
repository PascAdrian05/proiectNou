import { apiAuthRequest, apiRequest } from "./client";

export const reportService = {
  async createShareLink() {
    return apiAuthRequest("/reports/share", { method: "POST" });
  },

  async fetchSharedReport(shareToken) {
    return apiRequest(`/reports/public/${shareToken}`, { method: "GET" });
  },
};