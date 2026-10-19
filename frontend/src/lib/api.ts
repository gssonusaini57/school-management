import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import {
  clearAuth,
  decodeClaims,
  ensureFreshToken,
  getToken,
  saveUser,
  setAuthNotice,
  setToken,
  type AuthNotice,
} from "./auth";
import type { LoginResponse } from "@/types/api";

const baseURL = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

// withCredentials: the refresh token is an HttpOnly cookie scoped to the auth
// routes. The API is same-origin in every deployment, so this mostly states the
// intent — and keeps a future cross-origin dev setup working.
export const api = axios.create({ baseURL, timeout: 30000, withCredentials: true });

api.interceptors.request.use((cfg) => {
  const t = getToken();
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

// Full login path includes Vite's BASE_URL (e.g. "/admin/login" on prod, "/kisschool/admin/login" on TEST).
const LOGIN_PATH = (import.meta.env.BASE_URL || "/") + "login";

/**
 * Drop the local session and send the browser to the login page. A full
 * navigation (not a router push) so every in-memory state and open stream resets.
 * `notice` is what the login page tells the user; null for a silent redirect.
 */
export function signOut(notice: AuthNotice | null = "signedOut") {
  clearAuth();
  if (notice) setAuthNotice(notice);
  if (!location.pathname.endsWith("/login")) location.href = LOGIN_PATH;
}

// ── Refresh ──────────────────────────────────────────────────────────────────

let refreshing: Promise<boolean> | null = null;
const REFRESH_LOCK = "kis.auth.refresh";

/**
 * Trade the HttpOnly refresh cookie for a new access token (POST /auth/refresh,
 * empty body) and store it. Every refresh token is single-use, so refreshes are
 * serialised: one in-flight request per tab (concurrent callers share the
 * promise) and, where Web Locks exist, one per browser (two tabs rotating the
 * same cookie at once would race). Resolves true when a new token was stored;
 * false when there is no live session — no cookie, revoked, expired — when the
 * cookie now belongs to a different account than this tab's, or when the
 * network failed. Never rejects. Callers decide what false means for them.
 */
export function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = withBrowserLock(doRefresh)
      .catch(() => false) // never rejects: callers only ever need yes/no
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

async function doRefresh(): Promise<boolean> {
  // Who this tab is signed in as (an expired token still says). Read inside the
  // lock, so it reflects any refresh that just finished.
  const before = decodeClaims(getToken());
  try {
    // Bare axios on purpose: no Bearer (the cookie is the credential) and no 401 interceptor.
    const { data } = await axios.post<LoginResponse>(
      `${baseURL}/auth/refresh`,
      {},
      { withCredentials: true, timeout: 15_000 },
    );
    if (!data?.token) return false;
    // The browser keeps ONE refresh cookie, so someone signing in with "Remember
    // me" in another tab replaces it with theirs. A tab already signed in must never
    // be switched to that account by a refresh: for this tab the session is over.
    const after = decodeClaims(data.token);
    if (before?.sub != null && (String(after?.sub) !== String(before.sub) || after?.role !== before.role)) {
      return false;
    }
    setToken(data.token);
    // The server rebuilds the claims on every refresh, so class/menu edits land
    // here without a re-login.
    if (data.role) {
      saveUser({
        role: data.role,
        name: data.name,
        allowed_classes: data.allowed_classes ?? [],
        allowed_menus: data.allowed_menus ?? [],
      });
    }
    return true;
  } catch {
    return false;
  }
}

/**
 * Run `fn` under a browser-wide Web Lock. Web Locks are secure-context only (so
 * not on the plain-HTTP TEST instance); there, or when the lock itself can't be
 * taken, `fn` runs unlocked and the server's 60 s grace covers a two-tab race.
 */
function withBrowserLock<T>(fn: () => Promise<T>): Promise<T> {
  const locks = typeof navigator !== "undefined" ? navigator.locks : undefined;
  if (!locks) return fn();
  let ran = false;
  const locked = locks.request(REFRESH_LOCK, () => {
    ran = true;
    return fn();
  }) as Promise<T>;
  return locked.catch((e: unknown) => {
    if (ran) throw e;
    return fn();
  });
}

// ── 401 → refresh once → replay ──────────────────────────────────────────────

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };
// These answer 401 for their own reasons (wrong password, dead refresh token) — never refresh-and-retry them.
const AUTH_ROUTE = /\/auth\/(login|refresh|logout)(\?|$)/;

api.interceptors.response.use(
  (r) => r,
  async (err: AxiosError<{ detail?: unknown }>) => {
    const cfg = err.config as RetriableConfig | undefined;
    if (err.response?.status !== 401 || !cfg || AUTH_ROUTE.test(cfg.url ?? "")) throw err;
    // The access token was refused (expired or revoked): refresh once, then replay the request.
    if (!cfg._retried && (await refreshSession())) {
      cfg._retried = true;
      cfg.headers.Authorization = `Bearer ${getToken()}`;
      return api(cfg);
    }
    signOut();
    throw err;
  },
);

/**
 * A FastAPI error `detail` as one line of text. It isn't always a string:
 * request validation sends a list of {loc, msg}, and some endpoints send an
 * object with a `message`. Rendering either as-is crashes React.
 */
function detailText(detail: unknown): string {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        if (!d || typeof d !== "object" || !("msg" in d)) return typeof d === "string" ? d : JSON.stringify(d);
        const msg = String((d as { msg: unknown }).msg).replace(/^Value error, /, "");
        const loc = (d as { loc?: unknown }).loc;
        // ["body", "items", 0, "marks"] → "items.0.marks"
        const path = Array.isArray(loc) ? loc.map(String).filter((p, i) => i > 0 || !["body", "query", "path"].includes(p)) : [];
        return path.length && !msg.startsWith(path[0]) ? `${path.join(".")}: ${msg}` : msg;
      })
      .filter(Boolean)
      .join("; ");
  }
  if (typeof detail === "object") {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string" && message) return message;
    try {
      return JSON.stringify(detail);
    } catch {
      return String(detail);
    }
  }
  return String(detail);
}

/** The error to show for a failed request: always a string. */
export function apiError(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const data: unknown = e.response?.data;
    const detail = data && typeof data === "object" && "detail" in data ? (data as { detail: unknown }).detail : null;
    return detailText(detail) || e.message || "Network error";
  }
  return e instanceof Error ? e.message : "Unknown error";
}

/**
 * URL of a student document for <img>/<a>, which can't send a Bearer header, so
 * the JWT rides in the query. Async because a token about to expire is refreshed
 * first — the 401 interceptor never sees these requests.
 */
export async function fileUrl(studentId: number, kind: string): Promise<string> {
  const t = await ensureFreshToken();
  return `${baseURL}/files/students/${studentId}/${kind}/inline?token=${encodeURIComponent(t)}`;
}
