import axios, { AxiosError } from "axios";

const baseURL = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

export const api = axios.create({ baseURL, timeout: 30000 });

export const TOKEN_KEY = "kis_token";

// sessionStorage so the JWT dies with the tab/window — closing the browser
// logs the user out. Persistent autofill (identifier) still uses localStorage.
export function getToken(): string {
  return sessionStorage.getItem(TOKEN_KEY) ?? "";
}

export function setToken(t: string) {
  if (t) sessionStorage.setItem(TOKEN_KEY, t);
  else sessionStorage.removeItem(TOKEN_KEY);
}

api.interceptors.request.use((cfg) => {
  const t = getToken();
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

// Full login path includes Vite's BASE_URL (e.g. "/school/login" in prod, "/login" in greenfield dev).
const LOGIN_PATH = (import.meta.env.BASE_URL || "/") + "login";

api.interceptors.response.use(
  (r) => r,
  (err: AxiosError<{ detail?: string }>) => {
    if (err.response?.status === 401) {
      setToken("");
      if (!location.pathname.endsWith("/login")) location.href = LOGIN_PATH;
    }
    return Promise.reject(err);
  }
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

export function fileUrl(studentId: number, kind: string): string {
  const t = getToken();
  return `${baseURL}/files/students/${studentId}/${kind}/inline?token=${encodeURIComponent(t)}`;
}
