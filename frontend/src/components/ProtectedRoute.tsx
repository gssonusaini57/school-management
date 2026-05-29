import { Navigate, useLocation } from "react-router-dom";
import { useAuth, canAccessMenu } from "@/lib/auth";
import type { MenuKey } from "@/lib/menus";
import { ReactNode } from "react";

export function ProtectedRoute({
  children,
  adminOnly = false,
  superAdminOnly = false,
  menuKey,
}: {
  children: ReactNode;
  adminOnly?: boolean;
  superAdminOnly?: boolean;
  menuKey?: MenuKey;
}) {
  const { isAuthenticated, isAdmin, isSuperAdmin, user } = useAuth();
  const loc = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: loc }} replace />;
  if (superAdminOnly && !isSuperAdmin) return <Navigate to="/dashboard" replace />;
  if (adminOnly && !isAdmin) return <Navigate to="/dashboard" replace />;
  if (menuKey && !canAccessMenu(user, menuKey)) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
