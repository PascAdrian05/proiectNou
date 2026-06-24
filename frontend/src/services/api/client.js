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

  let response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && session.refreshToken) {
    try {
      const refreshedSession = await refreshSession(session.refreshToken);
      const retryHeaders = {
        ...buildHeaders(options),
        Authorization: `Bearer ${refreshedSession.accessToken}`,
      };

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
    const message = typeof payload === "string" ? payload : payload.detail || "Request failed";
    throw new Error(message);
  }

  return payload;
}
