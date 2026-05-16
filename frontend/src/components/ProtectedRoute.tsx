import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { ReactNode } from "react";

export function ProtectedRoute({
  children,
  adminOnly = false,
  superAdminOnly = false,
}: {
  children: ReactNode;
  adminOnly?: boolean;
  superAdminOnly?: boolean;
}) {
  const { isAuthenticated, isAdmin, isSuperAdmin } = useAuth();
  const loc = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: loc }} replace />;
  if (superAdminOnly && !isSuperAdmin) return <Navigate to="/dashboard" replace />;
  if (adminOnly && !isAdmin) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
