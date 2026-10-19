import { useEffect, useState, type ReactNode } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Login from "@/pages/Login";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import Dashboard from "@/pages/Dashboard";
import Admissions from "@/pages/Admissions";
import Students from "@/pages/Students";
import StudentDetail from "@/pages/StudentDetail";
import Attendance from "@/pages/Attendance";
import MarksEntry from "@/pages/MarksEntry";
import MarksResults from "@/pages/MarksResults";
import Fees from "@/pages/Fees";
import Notices from "@/pages/Notices";
import Staff from "@/pages/Staff";
import Reports from "@/pages/Reports";
import MobileApps from "@/pages/MobileApps";
import Letterheads from "@/pages/Letterheads";
import SalarySlips from "@/pages/SalarySlips";
import Templates from "@/pages/Templates";
import TemplateDetail from "@/pages/TemplateDetail";
import DeletionRequests from "@/pages/DeletionRequests";
import EditRequests from "@/pages/EditRequests";
import ClassSubjects from "@/pages/ClassSubjects";
import ClassSubjectDetail from "@/pages/ClassSubjectDetail";
import Sessions from "@/pages/Sessions";
import { Layout } from "@/components/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Toaster } from "@/components/ui/toaster";
import { Spinner } from "@/components/ui/spinner";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { UpdateBanner } from "@/components/UpdateBanner";
import { api, refreshSession } from "@/lib/api";
import {
  clearAuth,
  getToken,
  isTokenExpiringSoon,
  loadUser,
  saveUser,
  setAuthNotice,
  useSessionKeepAlive,
  type AuthUser,
} from "@/lib/auth";
import { useVersionCheck } from "@/lib/version";

// Pages that work without a session: never wait on a refresh to show them.
const PUBLIC_PATHS = new Set(["/login", "/forgot-password", "/reset-password"]);

/**
 * Restores a remembered sign-in before the protected routes render. A new tab (or
 * a tab whose token has run out) has no usable access token in sessionStorage,
 * but the browser may still hold the HttpOnly refresh cookie: one
 * POST /auth/refresh decides. Success continues to the requested route; failure
 * falls through to ProtectedRoute's usual redirect to /login.
 */
function AuthGate({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const [ready, setReady] = useState(
    () => PUBLIC_PATHS.has(pathname) || !isTokenExpiringSoon(getToken(), 0),
  );

  useEffect(() => {
    if (ready) return;
    let cancelled = false;
    (async () => {
      // A token that is here but dead means this tab WAS signed in.
      const hadToken = !!getToken();
      if (await refreshSession()) {
        // refreshSession stores the rebuilt claims too; /auth/me is the fallback
        // should a refresh ever come back without them.
        if (!loadUser()) {
          try {
            const { data } = await api.get<AuthUser>("/auth/me");
            saveUser({
              role: data.role,
              name: data.name,
              allowed_classes: data.allowed_classes ?? [],
              allowed_menus: data.allowed_menus ?? [],
            });
          } catch {
            // No user object → ProtectedRoute sends them to /login.
          }
        }
      } else if (hadToken) {
        // Drop the dead token so ProtectedRoute goes straight to /login (instead of
        // rendering a page whose first request fails), and say why there.
        clearAuth();
        setAuthNotice("signedOut");
      }
      if (!cancelled) setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [ready]);

  if (!ready) {
    return (
      <div
        role="status"
        aria-label={t("portal.auth.restoring", "Signing you in…")}
        className="min-h-screen flex items-center justify-center"
        style={{ background: "linear-gradient(135deg, var(--color-deep-indigo) 0%, var(--color-khalsa-blue) 100%)" }}
      >
        <Spinner className="h-8 w-8 text-white" />
      </div>
    );
  }
  return <>{children}</>;
}

export default function App() {
  // Auto-detect stale bundles after a deploy and hard-reload the user (a tab with
  // unsaved edits gets the UpdateBanner instead). No-op in dev (BUILD_ID === "dev")
  // or when version.json matches the bundle.
  useVersionCheck();
  // A remembered sign-in refreshes its access token shortly before it expires.
  useSessionKeepAlive();
  const { pathname } = useLocation();
  return (
    // One bad value or render error shows a message instead of a blank app.
    <ErrorBoundary resetKey={pathname}>
      <AuthGate>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"     element={<ProtectedRoute menuKey="dashboard"><Dashboard /></ProtectedRoute>} />
            <Route path="/admissions"    element={<ProtectedRoute menuKey="admissions"><Admissions /></ProtectedRoute>} />
            <Route path="/students"      element={<ProtectedRoute menuKey="students"><Students /></ProtectedRoute>} />
            <Route path="/students/:id"  element={<ProtectedRoute menuKey="students"><StudentDetail /></ProtectedRoute>} />
            <Route path="/attendance"    element={<ProtectedRoute menuKey="attendance"><Attendance /></ProtectedRoute>} />
            <Route path="/marks/entry"   element={<ProtectedRoute menuKey="marks-entry"><MarksEntry /></ProtectedRoute>} />
            <Route path="/marks/results" element={<ProtectedRoute menuKey="marks-results"><MarksResults /></ProtectedRoute>} />
            <Route path="/fees"          element={<ProtectedRoute menuKey="fees"><Fees /></ProtectedRoute>} />
            <Route path="/notices"       element={<ProtectedRoute menuKey="notices"><Notices /></ProtectedRoute>} />
            <Route path="/staff"         element={<ProtectedRoute adminOnly><Staff /></ProtectedRoute>} />
            <Route path="/reports"       element={<ProtectedRoute menuKey="reports"><Reports /></ProtectedRoute>} />
            <Route path="/letterheads"   element={<ProtectedRoute menuKey="letterheads"><Letterheads /></ProtectedRoute>} />
            <Route path="/salary-slips"  element={<ProtectedRoute menuKey="salary-slips"><SalarySlips /></ProtectedRoute>} />
            <Route path="/templates"     element={<ProtectedRoute menuKey="templates"><Templates /></ProtectedRoute>} />
            <Route path="/templates/:id" element={<ProtectedRoute menuKey="templates"><TemplateDetail /></ProtectedRoute>} />
            <Route path="/mobile-apps"   element={<ProtectedRoute menuKey="mobile-apps"><MobileApps /></ProtectedRoute>} />
            <Route path="/deletion-requests" element={<ProtectedRoute superAdminOnly><DeletionRequests /></ProtectedRoute>} />
            <Route path="/edit-requests"     element={<ProtectedRoute superAdminOnly><EditRequests /></ProtectedRoute>} />
            <Route path="/class-subjects"     element={<ProtectedRoute superAdminOnly><ClassSubjects /></ProtectedRoute>} />
            <Route path="/class-subjects/:id" element={<ProtectedRoute superAdminOnly><ClassSubjectDetail /></ProtectedRoute>} />
            <Route path="/sessions"           element={<ProtectedRoute superAdminOnly><Sessions /></ProtectedRoute>} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthGate>
      <Toaster />
      <UpdateBanner />
    </ErrorBoundary>
  );
}
