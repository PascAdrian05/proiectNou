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
  Menu,
  X,
} from "lucide-react";
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
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
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
      {/* Top Bar */}
      <header className="topbar">
        <div className="topbar-brand">
          <h1>{appConfig.appName}</h1>
        </div>

        {/* Desktop nav */}
        <nav className="topnav topnav-desktop">
          {isAuthenticated &&
            protectedLinks.map((link) => {
              const Icon = link.Icon;
              const isActive = location.pathname === link.to;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={isActive ? "nav-link active" : "nav-link"}
                  aria-current={isActive ? "page" : undefined}
                >
                  {Icon && <Icon size={16} strokeWidth={2} aria-hidden="true" />}
                  <span>{link.label}</span>
                </Link>
              );
            })}
        </nav>

        <div className="topbar-actions">
          <button type="button" className="icon-btn" onClick={toggleTheme} aria-label="Toggle theme">
            {isDark ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
          </button>

          {isAuthenticated && (
            <>
              <div className="user-badge">
                <span className="user-avatar">{(auth.email || auth.role || "U")[0].toUpperCase()}</span>
                <span className="user-email">{auth.email || ""}</span>
                <span className={`plan-tag plan-${auth.role === "owner" || auth.role === "admin" ? "pro" : "free"}`}>
                  {auth.role === "owner" || auth.role === "admin" ? "PRO" : "Free"}
                </span>
              </div>
              <button type="button" className="icon-btn" onClick={() => setShowLogoutConfirm(true)} title="Logout">
                <LogOut size={16} aria-hidden="true" />
              </button>
            </>
          )}

          {/* Mobile menu toggle */}
          {isAuthenticated && (
            <button
              type="button"
              className="icon-btn mobile-nav-toggle"
              onClick={() => setMobileNavOpen((v) => !v)}
              aria-label="Toggle navigation"
            >
              {mobileNavOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          )}
        </div>
      </header>

      {/* Mobile Navigation Drawer */}
      {isAuthenticated && mobileNavOpen && (
        <div className="mobile-overlay" onClick={() => setMobileNavOpen(false)}>
          <nav className="mobile-nav" onClick={(e) => e.stopPropagation()}>
            {protectedLinks.map((link) => {
              const Icon = link.Icon;
              const isActive = location.pathname === link.to;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`mobile-nav-link ${isActive ? "active" : ""}`}
                  onClick={() => setMobileNavOpen(false)}
                >
                  {Icon && <Icon size={18} strokeWidth={2} aria-hidden="true" />}
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      )}

      {/* Main Content */}
      <main className="content-wrap" key={location.pathname}>
        <Outlet />
      </main>

      {/* Logout Confirm Modal */}
      {showLogoutConfirm && (
        <div className="modal-overlay" onClick={() => setShowLogoutConfirm(false)}>
          <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
            <h3>Confirm logout</h3>
            <p>Are you sure you want to logout?</p>
            <div className="modal-actions">
              <button type="button" className="btn btn-primary" onClick={onLogout}>Logout</button>
              <button type="button" className="btn btn-ghost" onClick={() => setShowLogoutConfirm(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
