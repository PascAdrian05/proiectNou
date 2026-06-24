export const appConfig = {
  appName: "Security Monitor",
  // TODO: Bind your API base URL here for production.
  apiBaseUrl: "/api/v1",
  routes: {
    login: "/login",
    register: "/register",
    dashboard: "/dashboard",
    websites: "/websites",
    scans: "/scans",
    scanDetails: "/scans/:scanId",
    findings: "/findings",
    alerts: "/alerts",
    billing: "/billing",
    settings: "/settings",
    onboarding: "/onboarding",
    publicReport: "/public/report/:shareToken",
  },
};
