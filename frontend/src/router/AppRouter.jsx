import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AppLayout } from "../layouts/AppLayout";
import { appConfig } from "../config/appConfig";

const LoginPage = lazy(() => import("../pages/LoginPage").then((module) => ({ default: module.LoginPage })));
const RegisterPage = lazy(() => import("../pages/RegisterPage").then((module) => ({ default: module.RegisterPage })));
const DashboardPage = lazy(() => import("../pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const WebsitesPage = lazy(() => import("../pages/WebsitesPage").then((module) => ({ default: module.WebsitesPage })));
const ScansPage = lazy(() => import("../pages/ScansPage").then((module) => ({ default: module.ScansPage })));
const ScanDetailsPage = lazy(() => import("../pages/ScanDetailsPage").then((module) => ({ default: module.ScanDetailsPage })));
const FindingsPage = lazy(() => import("../pages/FindingsPage").then((module) => ({ default: module.FindingsPage })));
const AlertsPage = lazy(() => import("../pages/AlertsPage").then((module) => ({ default: module.AlertsPage })));
const BillingPage = lazy(() => import("../pages/BillingPage").then((module) => ({ default: module.BillingPage })));
const SettingsPage = lazy(() => import("../pages/SettingsPage").then((module) => ({ default: module.SettingsPage })));
const OnboardingPage = lazy(() => import("../pages/OnboardingPage").then((module) => ({ default: module.OnboardingPage })));
const PublicReportPage = lazy(() => import("../pages/PublicReportPage").then((module) => ({ default: module.PublicReportPage })));
const SecurityPage = lazy(() => import("../pages/SecurityPage").then((module) => ({ default: module.SecurityPage })));
const StatusPage = lazy(() => import("../pages/StatusPage").then((module) => ({ default: module.StatusPage })));

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to={appConfig.routes.login} replace />;
  }

  return children;
}

function GuestRoute({ children }) {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to={appConfig.routes.dashboard} replace />;
  }

  return children;
}

function RootRedirect() {
  const { isAuthenticated } = useAuth();
  return <Navigate to={isAuthenticated ? appConfig.routes.dashboard : appConfig.routes.login} replace />;
}

function RouteLoader() {
  return <p className="route-loader">Loading module...</p>;
}

function LazyRoute({ children }) {
  return <Suspense fallback={<RouteLoader />}>{children}</Suspense>;
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />

      <Route
        path={appConfig.routes.publicReport}
        element={
          <LazyRoute>
            <PublicReportPage />
          </LazyRoute>
        }
      />

      <Route
        path={appConfig.routes.login}
        element={
          <GuestRoute>
            <LazyRoute>
              <div className="auth-standalone"><LoginPage /></div>
            </LazyRoute>
          </GuestRoute>
        }
      />
      <Route
        path={appConfig.routes.register}
        element={
          <GuestRoute>
            <LazyRoute>
              <div className="auth-standalone"><RegisterPage /></div>
            </LazyRoute>
          </GuestRoute>
        }
      />

      <Route element={<AppLayout />}>
        <Route
          path={appConfig.routes.dashboard}
          element={
            <ProtectedRoute>
              <LazyRoute>
                <DashboardPage />
              </LazyRoute>
            </ProtectedRoute>
          }
        />
        <Route
          path={appConfig.routes.websites}
          element={
            <ProtectedRoute>
              <LazyRoute>
                <WebsitesPage />
              </LazyRoute>
            </ProtectedRoute>
          }
        />
        <Route
          path={appConfig.routes.scans}
          element={
            <ProtectedRoute>
              <LazyRoute>
                <ScansPage />
              </LazyRoute>
            </ProtectedRoute>
          }
        />
        <Route
          path={appConfig.routes.scanDetails}
          element={
            <ProtectedRoute>
              <LazyRoute>
                <ScanDetailsPage />
              </LazyRoute>
            </ProtectedRoute>
          }
        />
        <Route
          path={appConfig.routes.findings}
          element={
            <ProtectedRoute>
              <LazyRoute>
                <FindingsPage />
              </LazyRoute>
            </ProtectedRoute>
          }
        />
        <Route
          path={appConfig.routes.alerts}
          element={
            <ProtectedRoute>
              <LazyRoute>
                <AlertsPage />
              </LazyRoute>
            </ProtectedRoute>
          }
        />
        <Route
          path={appConfig.routes.billing}
          element={
            <ProtectedRoute>
              <LazyRoute>
                <BillingPage />
              </LazyRoute>
            </ProtectedRoute>
          }
        />
        <Route
          path={appConfig.routes.settings}
          element={
            <ProtectedRoute>
              <LazyRoute>
                <SettingsPage />
              </LazyRoute>
            </ProtectedRoute>
          }
        />
        <Route
          path={appConfig.routes.onboarding}
          element={
            <ProtectedRoute>
              <LazyRoute>
                <OnboardingPage />
              </LazyRoute>
            </ProtectedRoute>
          }
        />
        <Route
          path={appConfig.routes.security}
          element={
            <LazyRoute>
              <SecurityPage />
            </LazyRoute>
          }
        />
        <Route
          path={appConfig.routes.status}
          element={
            <LazyRoute>
              <StatusPage />
            </LazyRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to={appConfig.routes.login} replace />} />
    </Routes>
  );
}
