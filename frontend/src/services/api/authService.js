import { apiAuthRequest, apiRequest } from "./client";

export const authService = {
  async register(payload) {
    // TODO: Bind your API data here if backend payload changes.
    return apiRequest("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async login(payload) {
    const form = new URLSearchParams();
    form.append("username", payload.email);
    form.append("password", payload.password);

    return apiRequest("/auth/login", {
      method: "POST",
      body: form,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
  },

  async logout(payload) {
    return apiAuthRequest("/auth/logout", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async refresh(payload) {
    return apiRequest("/auth/refresh", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
