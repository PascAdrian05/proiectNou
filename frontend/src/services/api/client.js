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

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json")
    ? await response.json()
    : await response.text();
}

function errorFromPayload(payload, fallback) {
  if (typeof payload === "string") return payload || fallback;
  if (payload && typeof payload === "object" && payload.detail) return payload.detail;
  return fallback;
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
    ...options,
    headers: buildHeaders(options),
  });

  const payload = await parseResponse(response);

  if (!response.ok) {
    throw new Error(errorFromPayload(payload, "Request failed"));
  }

  return payload;
}

// Single in-flight refresh promise so concurrent 401s don't all try to
// refresh simultaneously (which produces token thrash and extra refresh
// revocations).
let refreshInFlight = null;

async function performRefresh() {
  const { refreshToken } = storage.getAuthSession();
  if (!refreshToken) {
    throw new Error("No refresh token");
  }

  const response = await fetch(`${appConfig.apiBaseUrl}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    throw new Error("Session refresh failed");
  }

  const payload = await parseResponse(response);
  const current = storage.getAuthSession();

  const nextSession = {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token || current.refreshToken || "",
    role: payload.role || current.role || "",
    tenantId: payload.tenant_id || current.tenantId || "",
    stepUpToken: current.stepUpToken || "",
  };

  storage.setAuthSession(nextSession);
  return nextSession;
}

async function refreshSession() {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = performRefresh().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export async function apiAuthRequest(path, options = {}) {
  let session = storage.getAuthSession();
  const headers = buildHeaders(options);

  if (session.accessToken) {
    headers.Authorization = `Bearer ${session.accessToken}`;
  }

  if (session.stepUpToken) {
    headers["X-Step-Up-Token"] = session.stepUpToken;
  }

  let response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
    ...options,
    headers,
  });

  // Step-up required — surface a typed error so the UI can prompt for 2FA.
  if (response.status === 401 && response.headers.get("X-Step-Up-Required") === "true") {
    const error = new Error("Step-up authentication required");
    error.stepUpRequired = true;
    throw error;
  }

  // Token expired — try to refresh once, then retry the original request.
  if (response.status === 401 && session.refreshToken) {
    try {
      const refreshedSession = await refreshSession();
      const retryHeaders = {
        ...buildHeaders(options),
        Authorization: `Bearer ${refreshedSession.accessToken}`,
      };

      if (refreshedSession.stepUpToken) {
        retryHeaders["X-Step-Up-Token"] = refreshedSession.stepUpToken;
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

  const payload = await parseResponse(response);

  if (!response.ok) {
    if (response.headers.get("X-Step-Up-Required") === "true") {
      const error = new Error("Step-up authentication required");
      error.stepUpRequired = true;
      throw error;
    }
    throw new Error(errorFromPayload(payload, "Request failed"));
  }

  // Refreshed mid-flight: pick up any new tokens other callers persisted.
  session = storage.getAuthSession();

  return payload;
}