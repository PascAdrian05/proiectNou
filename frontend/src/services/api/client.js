import { appConfig } from "../../config/appConfig";
import { storage } from "../storage";

function isBodyWithoutJsonContentType(body) {
  return body instanceof FormData || body instanceof URLSearchParams;
}

function buildHeaders(options) {
  const headers = {
    ...(options.headers || {}),
  };

  if (!headers["Content-Type"] && !isBodyWithoutJsonContentType(options.body)) {
    headers["Content-Type"] = "application/json";
  }

  return headers;
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
    ...options,
    headers: buildHeaders(options),
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof payload === "string" ? payload : payload.detail || "Request failed";
    throw new Error(message);
  }

  return payload;
}

async function refreshSession(refreshToken) {
  const response = await fetch(`${appConfig.apiBaseUrl}/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    throw new Error("Session refresh failed");
  }

  const payload = await response.json();
  const current = storage.getAuthSession();

  const nextSession = {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token || current.refreshToken || "",
    role: payload.role || current.role || "",
    tenantId: payload.tenant_id || current.tenantId || "",
  };

  storage.setAuthSession(nextSession);
  return nextSession;
}

export async function apiAuthRequest(path, options = {}) {
  const session = storage.getAuthSession();
  const headers = buildHeaders(options);

  if (session.accessToken) {
    headers.Authorization = `Bearer ${session.accessToken}`;
  }

  // If we have a step-up token, attach it
  if (session.stepUpToken) {
    headers["X-Step-Up-Token"] = session.stepUpToken;
  }

  let response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
    ...options,
    headers,
  });

  // Check if step-up authentication is required
  if (response.status === 401 && response.headers.get("X-Step-Up-Required") === "true") {
    const error = new Error("Step-up authentication required");
    error.stepUpRequired = true;
    throw error;
  }

  if (response.status === 401 && session.refreshToken) {
    try {
      const refreshedSession = await refreshSession(session.refreshToken);
      const retryHeaders = {
        ...buildHeaders(options),
        Authorization: `Bearer ${refreshedSession.accessToken}`,
      };

      if (session.stepUpToken) {
        retryHeaders["X-Step-Up-Token"] = session.stepUpToken;
      }

      response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
        ...options,
        headers: retryHeaders,
      });
    } catch {
      storage.clearAuthSession();
      throw new Error("Session expired. Please login again.");
    }
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    // Check again for step-up required (in case refresh didn't trigger it)
    if (response.headers.get("X-Step-Up-Required") === "true") {
      const error = new Error("Step-up authentication required");
      error.stepUpRequired = true;
      throw error;
    }
    const message = typeof payload === "string" ? payload : payload.detail || "Request failed";
    throw new Error(message);
  }

  return payload;
}
