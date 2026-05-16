import { useEffect, useState } from "react";
import { setToken, getToken } from "./api";
import type { Role } from "@/types/api";

export interface AuthUser {
  role: Role;
  name: string;
  allowed_classes: string[];
}

const USER_KEY = "kis_user";
const REMEMBER_KEY = "kis_remember";

export function loadUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function saveAuth(token: string, user: AuthUser) {
  setToken(token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  setToken("");
  localStorage.removeItem(USER_KEY);
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

  useEffect(() => {
    const onStorage = () => setUser(loadUser());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

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
