import { apiAuthRequest } from "./client";

export const userService = {
  async getProfile() {
    return apiAuthRequest("/users/me", { method: "GET" });
  },
};
