import { useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Globe,
  Search,
  AlertTriangle,
  Bell,
  CreditCard,
  Settings,
  Shield,
  Sun,
  Moon,
  LogOut,
} from "lucide-react";
import { BehaviorTracker } from "../components/BehaviorTracker";
import { LiveUsersBadge } from "../components/LiveUsersBadge";
import { TrustBadge } from "../components/TrustBadge";
import SecurityBadge from "../components/SecurityBadge";
import StepUpModal from "../components/StepUpModal";
import AIAssistant from "../components/AIAssistant";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { authService } from "../services/api/authService";
import { appConfig } from "../config/appConfig";

const protectedLinks = [
  { to: appConfig.routes.dashboard, label: "Dashboard", Icon: LayoutDashboard },
  { to: appConfig.routes.websites, label: "Websites", Icon: Globe },
  { to: appConfig.routes.scans, label: "Scans", Icon: Search },
  { to: appConfig.routes.findings, label: "Findings", Icon: AlertTriangle },
  { to: appConfig.routes.alerts, label: "Alerts", Icon: Bell },
  { to: appConfig.routes.billing, label: "Billing", Icon: CreditCard },
  { to: appConfig.routes.settings, label: "Settings", Icon: Settings },
  { to: appConfig.routes.security, label: "Security", Icon: Shield },
];

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, auth, clearSession } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const [showAccount, setShowAccount] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

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
        <div className="topbar-brand">
          <h1>{appConfig.appName}</h1>
          {isAuthenticated && (
            <span className={`plan-badge plan-${auth.role === "owner" || auth.role === "admin" ? "pro" : "free"}`}>
              {auth.role === "owner" || auth.role === "admin" ? "PRO" : "Free"}
            </span>
          )}
        </div>
        <nav className="topnav">
          {isAuthenticated && protectedLinks.map((link) => {
            const Icon = link.Icon;
            const isActive = location.pathname === link.to;
            return (
              <Link
                key={link.to}
                className={isActive ? "active" : ""}
                to={link.to}
                aria-current={isActive ? "page" : undefined}
              >
                {Icon && <Icon size={16} strokeWidth={2} aria-hidden="true" />}
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="topbar-actions">
          <button type="button" className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
            {isDark ? <><Sun size={14} aria-hidden="true" /> Light</> : <><Moon size={14} aria-hidden="true" /> Dark</>}
          </button>
          {isAuthenticated && (
            <>
              <button type="button" className="account-btn" onClick={() => setShowAccount((v) => !v)} title="Account details" aria-label="Account details">
                <span className="account-avatar">{(auth.email || auth.role || "U")[0].toUpperCase()}</span>
              </button>
              <button type="button" className="ghost-button" onClick={() => setShowLogoutConfirm(true)}>
                <LogOut size={14} aria-hidden="true" /> Logout
              </button>
            </>
          )}
        </div>
      </header>
      {isAuthenticated && <BehaviorTracker />}
      {isAuthenticated && <LiveUsersBadge />}
      {isAuthenticated && <TrustBadge />}
      {isAuthenticated && <SecurityBadge />}
      {isAuthenticated && <AIAssistant />}

      <main className="content-wrap" key={location.pathname}>
        <Outlet />
      </main>

      {showAccount && (
        <div className="overlay-panel" onClick={() => setShowAccount(false)}>
          <div className="account-panel" onClick={(e) => e.stopPropagation()}>
            <h3>Account</h3>
            <div className="account-details">
              <div className="account-field">
                <span className="account-label">Email</span>
                <span className="account-value">{auth.email || auth.tenantId || "—"}</span>
              </div>
              <div className="account-field">
                <span className="account-label">Role</span>
                <span className="account-value account-role">{(auth.role || "user").toUpperCase()}</span>
              </div>
              <div className="account-field">
                <span className="account-label">Plan</span>
                <span className={`account-value plan-badge plan-${auth.role === "owner" || auth.role === "admin" ? "pro" : "free"}-lg`}>
                  {auth.role === "owner" || auth.role === "admin" ? "PRO" : "Free"}
                </span>
              </div>
              <div className="account-field">
                <span className="account-label">Tenant</span>
                <span className="account-value account-mono">{auth.tenantId ? auth.tenantId.slice(0, 12) + "…" : "—"}</span>
              </div>
            </div>
            <button type="button" className="ghost-button" onClick={() => { setShowAccount(false); navigate(appConfig.routes.billing); }}>
              Manage billing
            </button>
          </div>
        </div>
      )}

      {showLogoutConfirm && (
        <div className="overlay-panel" onClick={() => setShowLogoutConfirm(false)}>
          <div className="confirm-panel" onClick={(e) => e.stopPropagation()}>
            <p>Are you sure you want to logout?</p>
            <div className="confirm-actions">
              <button type="button" onClick={onLogout}>Logout</button>
              <button type="button" className="ghost-button" onClick={() => setShowLogoutConfirm(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}