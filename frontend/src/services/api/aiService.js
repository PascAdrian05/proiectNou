import { apiAuthRequest } from "./client";

export const aiService = {
  async getStatus() {
    return apiAuthRequest("/ai/status", { method: "GET" });
  },

  async analyzeFinding(findingId) {
    return apiAuthRequest(`/ai/analyze-finding/${findingId}`, { method: "POST" });
  },

  async getSecurityTips() {
    return apiAuthRequest("/ai/security-tips", { method: "POST" });
  },

  async verifyPosture() {
    return apiAuthRequest("/ai/verify-posture", { method: "POST" });
  },

  async listConversations() {
    return apiAuthRequest("/ai/conversations/", { method: "GET" });
  },

  async getConversation(conversationId) {
    return apiAuthRequest(`/ai/conversations/${conversationId}`, { method: "GET" });
  },

  async createConversation(payload) {
    return apiAuthRequest("/ai/conversations/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateConversation(conversationId, payload) {
    return apiAuthRequest(`/ai/conversations/${conversationId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async deleteConversation(conversationId) {
    return apiAuthRequest(`/ai/conversations/${conversationId}`, { method: "DELETE" });
  },
};
