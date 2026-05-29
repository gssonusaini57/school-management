import { useState } from "react";
import { setToken, getToken } from "./api";
import type { Role } from "@/types/api";
import type { MenuKey } from "@/lib/menus";

export interface AuthUser {
  role: Role;
  name: string;
  allowed_classes: string[];
  allowed_menus?: string[];
}

// Admin + super-admin bypass menu grants — they always see everything.
export function canAccessMenu(
  user: { role?: Role; allowed_menus?: string[] } | null | undefined,
  key: MenuKey | string,
): boolean {
  if (!user) return false;
  if (user.role === "admin" || user.role === "super_admin") return true;
  return Array.isArray(user.allowed_menus) && user.allowed_menus.includes(key);
}

const USER_KEY = "kis_user";
const REMEMBER_KEY = "kis_remember";

export function loadUser(): AuthUser | null {
  const raw = sessionStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function saveAuth(token: string, user: AuthUser) {
  setToken(token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  setToken("");
  sessionStorage.removeItem(USER_KEY);
}

export function saveRemember(payload: object | null) {
  if (payload) localStorage.setItem(REMEMBER_KEY, JSON.stringify(payload));
  else localStorage.removeItem(REMEMBER_KEY);
}

export function loadRemember(): { identifier?: string } | null {
  const raw = localStorage.getItem(REMEMBER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(loadUser());

  return {
    user,
    isAuthenticated: !!getToken() && !!user,
    // Super-admin inherits admin powers across the UI; only the queue page
    // checks `isSuperAdmin` specifically.
    isAdmin: user?.role === "admin" || user?.role === "super_admin",
    isSuperAdmin: user?.role === "super_admin",
    setUser: (u: AuthUser | null) => {
      if (u) saveAuth(getToken(), u);
      else clearAuth();
      setUser(u);
    },
  };
}
