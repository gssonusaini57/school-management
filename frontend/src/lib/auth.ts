import { useEffect, useMemo, useSyncExternalStore } from "react";
// api.ts imports the token store from here and this file calls api.ts's
// refreshSession(); the cycle is safe because neither side touches the other at
// module-evaluation time (only inside functions).
import { refreshSession } from "./api";
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

// ── Access token: a tiny reactive store backed by sessionStorage ─────────────
//
// sessionStorage so the one-hour JWT dies with the tab/window. What survives is
// the HttpOnly refresh cookie the server sets for a "Remember me" sign-in, and
// refreshSession() (api.ts) trades it for a new JWT whenever this one is about to
// expire or has just been refused. Anything that embeds the token in a URL
// (<img>, downloads, EventSource) reads it through useToken() so it follows a
// rotation instead of keeping a dead copy.

export const TOKEN_KEY = "kis_token";
// Server clock minus this browser's clock (ms), measured when the token arrived.
const SKEW_KEY = "kis_token_skew";
const USER_KEY = "kis_user";
const REMEMBER_KEY = "kis_remember";
const NOTICE_KEY = "kis_auth_notice";

// One listener set for the whole auth store (token + user); each hook's
// snapshot decides whether a change concerns it.
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((listener) => listener());
}

function readSession(key: string): string {
  try {
    return sessionStorage.getItem(key) ?? "";
  } catch {
    return "";
  }
}

function writeSession(key: string, value: string) {
  try {
    if (value) sessionStorage.setItem(key, value);
    else sessionStorage.removeItem(key);
  } catch {
    // Storage blocked (private mode on an old browser): the app still works for this page load.
  }
}

export function getToken(): string {
  return readSession(TOKEN_KEY);
}

export function setToken(t: string) {
  const next = t || "";
  if (next === getToken()) return;
  writeSession(TOKEN_KEY, next);
  // A new session supersedes a pending "your session ended" notice.
  if (next) writeSession(NOTICE_KEY, "");
  // Only a NEW token is measured: re-saving the same one later would understate the skew.
  const iat = next ? decodeClaims(next)?.iat : undefined;
  writeSession(SKEW_KEY, typeof iat === "number" ? String(iat * 1000 - Date.now()) : "");
  notify();
}

/**
 * How far the server's clock runs ahead of this browser's (negative when behind),
 * from the current token's `iat`. Expiry checks use it so a PC whose clock is off
 * by an hour or more (wrong time zone "fixed" by hand) neither sees every fresh
 * token as expired (and refreshes in a loop) nor trusts a dead one.
 */
function clockSkewMs(): number {
  const n = Number(readSession(SKEW_KEY));
  return Number.isFinite(n) ? n : 0;
}

/** Run `listener` after every token change (login, refresh, logout). Returns the unsubscribe. */
export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** The current access token, re-rendering the component whenever it changes. */
export function useToken(): string {
  return useSyncExternalStore(subscribe, getToken, getToken);
}

// ── JWT claims (read-only; the server is the one that verifies) ──────────────

export interface TokenClaims {
  sub?: string;
  role?: string;
  iat?: number;
  exp?: number;
  sid?: number | null;
}

/** The payload of a JWT, decoded without verifying it (base64url → JSON); null when unreadable. */
export function decodeClaims(token: string): TokenClaims | null {
  const part = token.split(".")[1];
  if (!part) return null;
  try {
    const b64 = part.replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const bytes = Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes)) as TokenClaims;
  } catch {
    return null;
  }
}

/** Refresh this long before the access token expires. */
export const REFRESH_AHEAD_MS = 2 * 60_000;

/**
 * When `token` expires, in this browser's clock (epoch ms, corrected by the
 * measured server skew), or null when it carries no readable `exp`.
 */
export function tokenExpiresAt(token: string = getToken()): number | null {
  const exp = decodeClaims(token)?.exp;
  return typeof exp === "number" ? exp * 1000 - clockSkewMs() : null;
}

/**
 * True when there is no token, or it expires within `withinMs` (default 2 minutes).
 * An unreadable token counts as expiring: the server would refuse it anyway.
 */
export function isTokenExpiringSoon(token: string = getToken(), withinMs: number = REFRESH_AHEAD_MS): boolean {
  if (!token) return true;
  const at = tokenExpiresAt(token);
  return at === null || at - Date.now() < withinMs;
}

/** True when the token was minted from a device session ("Remember me"), i.e. a refresh cookie should exist. */
export function tokenHasSession(token: string = getToken()): boolean {
  return decodeClaims(token)?.sid != null;
}

/**
 * The access token to use right now, refreshed first when it is about to expire.
 * For URLs that embed the token (`?token=`), where the 401 interceptor can't help.
 * Resolves to "" when there is no session at all.
 */
export async function ensureFreshToken(): Promise<string> {
  if (isTokenExpiringSoon()) await refreshSession();
  return getToken();
}

/**
 * Keeps a remembered sign-in's access token fresh while the tab is open: refreshes
 * REFRESH_AHEAD_MS before it expires and when the tab comes back into view, so
 * token-in-URL links and the first click after a long idle don't hit a dead token.
 * Only tokens minted from a device session are refreshed this way — a plain
 * sign-in has no cookie to refresh with. A failed refresh is not retried here; the
 * 401 interceptor is the backstop.
 */
export function useSessionKeepAlive() {
  const token = useToken();
  useEffect(() => {
    if (!token || !tokenHasSession(token)) return;
    const at = tokenExpiresAt(token);
    if (at === null) return;
    // Refreshing only while visible: a tab left open in the background doesn't
    // keep sliding the 30-day session forward on its own.
    const refresh = () => {
      if (document.visibilityState !== "hidden") void refreshSession();
    };
    const delay = at - REFRESH_AHEAD_MS - Date.now();
    let timer: number | undefined;
    if (delay <= 0) refresh();
    else timer = window.setTimeout(refresh, Math.min(delay, 0x7fffffff));
    const onVisibility = () => {
      if (document.visibilityState === "visible" && isTokenExpiringSoon(token)) refresh();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [token]);
}

// ── Signed-in user (claims mirror, for menus and guards) ─────────────────────

function readUserRaw(): string {
  return readSession(USER_KEY);
}

function parseUser(raw: string): AuthUser | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function loadUser(): AuthUser | null {
  return parseUser(readUserRaw());
}

export function saveUser(user: AuthUser) {
  const next = JSON.stringify(user);
  const changed = next !== readUserRaw();
  writeSession(USER_KEY, next);
  if (changed) notify();
}

export function saveAuth(token: string, user: AuthUser) {
  setToken(token);
  saveUser(user);
}

export function clearAuth() {
  writeSession(USER_KEY, "");
  writeSession(TOKEN_KEY, "");
  writeSession(SKEW_KEY, "");
  notify();
}

// ── Notice for the login page (survives the full-page redirect) ──────────────

export type AuthNotice = "signedOut";

export function setAuthNotice(notice: AuthNotice) {
  writeSession(NOTICE_KEY, notice);
}

/**
 * The pending notice, if any (pure: safe to call during render). It stays until
 * the next sign-in — setToken() clears it — rather than being consumed when the
 * login page mounts: signOut()'s store update can mount the login page inside the
 * old document an instant before its full-page redirect lands, and consuming it
 * there would leave the freshly loaded page with nothing to say.
 */
export function peekAuthNotice(): AuthNotice | null {
  return readSession(NOTICE_KEY) === "signedOut" ? "signedOut" : null;
}

// ── "Remember me": the identifier autofill lives in localStorage ─────────────

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

/** A short name for this browser, e.g. "Chrome on macOS" — what GET /auth/sessions lists for it. */
export function deviceName(ua: string = typeof navigator === "undefined" ? "" : navigator.userAgent): string {
  const browser = /Edg\//.test(ua)
    ? "Edge"
    : /OPR\/|Opera/.test(ua)
      ? "Opera"
      : /SamsungBrowser/.test(ua)
        ? "Samsung Internet"
        : /Chrome\/|CriOS\//.test(ua)
          ? "Chrome"
          : /Firefox\/|FxiOS\//.test(ua)
            ? "Firefox"
            : /Safari\//.test(ua)
              ? "Safari"
              : "Browser";
  // Android before Linux (its UA contains both); iPad before Mac (older iPad UAs say Macintosh).
  const os = /Windows/.test(ua)
    ? "Windows"
    : /Android/.test(ua)
      ? "Android"
      : /iPhone|iPod/.test(ua)
        ? "iPhone"
        : /iPad/.test(ua)
          ? "iPad"
          : /Mac OS X|Macintosh/.test(ua)
            ? "macOS"
            : /CrOS/.test(ua)
              ? "ChromeOS"
              : /Linux/.test(ua)
                ? "Linux"
                : "";
  return os ? `${browser} on ${os}` : browser;
}

export function useAuth() {
  // Both live: a sign-in, sign-out or a refresh that rebuilt the claims
  // (classes/menus) re-renders every consumer.
  const token = useToken();
  const rawUser = useSyncExternalStore(subscribe, readUserRaw, readUserRaw);
  const user = useMemo(() => parseUser(rawUser), [rawUser]);

  return {
    user,
    isAuthenticated: !!token && !!user,
    // Super-admin inherits admin powers across the UI; only the queue page
    // checks `isSuperAdmin` specifically.
    isAdmin: user?.role === "admin" || user?.role === "super_admin",
    isSuperAdmin: user?.role === "super_admin",
    setUser: (u: AuthUser | null) => {
      if (u) saveAuth(getToken(), u);
      else clearAuth();
    },
  };
}
