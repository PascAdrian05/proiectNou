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
  const url = `${appConfig.apiBaseUrl}${path}`;

  if (!response.ok) {
    throw new Error(errorFromPayload(payload, `Request failed (${response.status}) on ${url}`));
  }

  return payload;
}

// Single in-flight refresh promise so concurrent 401s don't all try to
// refresh simultaneously (which produces token thrash and extra refresh
// revocations).
let refreshInFlight = null;

function shouldClearSessionOnRefreshFailure(path) {
  // Only wipe the session on refresh failure when the original request
  // actually requires auth. Public endpoints (login, refresh itself,
  // register, password reset, oauth) must never log the user out — that
  // causes the "page flashes and disappears" symptom when the backend
  // is unreachable or returns an unrelated 401.
  if (!path) return true;
  const publicPrefixes = [
    "/auth/login",
    "/auth/register",
    "/auth/refresh",
    "/auth/forgot",
    "/auth/reset",
    "/auth/verify",
    "/oauth/",
  ];
  return !publicPrefixes.some((prefix) => path.startsWith(prefix));
}

async function performRefresh() {
  const { refreshToken } = storage.getAuthSession();
  if (!refreshToken) {
    throw new Error("No refresh token");
  }

  let response;
  try {
    response = await fetch(`${appConfig.apiBaseUrl}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch (networkError) {
    // Network failure — don't wipe the session, the backend may be
    // transiently unavailable. Surface a clear error instead.
    throw new Error("Backend unreachable. Try again in a moment.");
  }

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

  let response;
  try {
    response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
      ...options,
      headers,
    });
  } catch (networkError) {
    // Network failure — don't clear the session, let the UI render an
    // error message instead of bouncing the user back to /login.
    throw new Error("Backend unreachable. Check that the API is running.");
  }

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
    } catch (refreshError) {
      // Only wipe the session when this was a genuine auth failure on a
      // protected endpoint. Public endpoints and network failures must
      // preserve the session so the user isn't kicked out unexpectedly.
      if (shouldClearSessionOnRefreshFailure(path)) {
        storage.clearAuthSession();
      }
      throw new Error(refreshError.message || "Session expired. Please login again.");
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