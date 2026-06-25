import { useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { BehaviorTracker } from "../components/BehaviorTracker";
import { LiveUsersBadge } from "../components/LiveUsersBadge";
import { TrustBadge } from "../components/TrustBadge";
import SecurityBadge from "../components/SecurityBadge";
import StepUpModal from "../components/StepUpModal";
import { AIAssistant } from "../components/AIAssistant";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { authService } from "../services/api/authService";
import { appConfig } from "../config/appConfig";
import { storage } from "../services/storage";

const publicLinks = [
  { to: appConfig.routes.login, label: "Login" },
  { to: appConfig.routes.register, label: "Register" },
];

const protectedLinks = [
  { to: appConfig.routes.dashboard, label: "Dashboard" },
  { to: appConfig.routes.websites, label: "Websites" },
  { to: appConfig.routes.scans, label: "Scans" },
  { to: appConfig.routes.findings, label: "Findings" },
  { to: appConfig.routes.alerts, label: "Alerts" },
  { to: appConfig.routes.settings, label: "Settings" },
  { to: appConfig.routes.billing, label: "Billing" },
  { to: appConfig.routes.security, label: "Security" },
];

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, auth, clearSession } = useAuth();
  const { isDark, toggleTheme } = useTheme();

  const links = isAuthenticated ? protectedLinks : publicLinks;

  async function onLogout() {
    try {
      if (auth.refreshToken) {
        await authService.logout({ refresh_token: auth.refreshToken });
      }
    } finally {
      clearSession();
      navigate(appConfig.routes.login);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>{appConfig.appName}</h1>
          <p className="subtitle">
            {isAuthenticated
              ? `Signed in as ${auth.role || "user"} · Tenant ${auth.tenantId?.slice(0, 8) || "—"}…`
              : "Security monitoring platform"}
          </p>
        </div>
        <div className="topbar-actions">
          <button type="button" className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
            {isDark ? "☀ Light" : "☾ Dark"}
          </button>
          {isAuthenticated && (
            <button type="button" className="ghost-button" onClick={onLogout}>
              Logout
            </button>
          )}
        </div>
        <nav className="topnav">
          {links.map((link) => (
            <Link key={link.to} className={location.pathname === link.to ? "active" : ""} to={link.to}>
              {link.label}
            </Link>
          ))}
        </nav>
        <TrustBadge />
        {isAuthenticated && <SecurityBadge />}
        {isAuthenticated && <LiveUsersBadge />}
      </header>
      {isAuthenticated && <BehaviorTracker />}
      {isAuthenticated && <AIAssistant />}
      <main className="content-wrap">
        <Outlet />
      </main>
    </div>
  );
}
