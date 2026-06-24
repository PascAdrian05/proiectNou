import { apiAuthRequest } from "./client";

export const billingService = {
  async getSubscription() {
    return apiAuthRequest("/billing/subscription", { method: "GET" });
  },

  async createCheckoutSession(plan) {
    const origin = window.location.origin;
    return apiAuthRequest("/billing/stripe/checkout-session", {
      method: "POST",
      body: JSON.stringify({
        plan,
        success_url: `${origin}/billing?status=success`,
        cancel_url: `${origin}/billing?status=cancel`,
      }),
    });
  },

  async openPortal() {
    return apiAuthRequest("/billing/stripe/portal", { method: "POST" });
  },
};
