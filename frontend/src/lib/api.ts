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

export function apiError(e: unknown): string {
  if (axios.isAxiosError(e)) {
    return e.response?.data?.detail ?? e.message ?? "Network error";
  }
  return e instanceof Error ? e.message : "Unknown error";
}

export function fileUrl(studentId: number, kind: string): string {
  const t = getToken();
  return `${baseURL}/files/students/${studentId}/${kind}/inline?token=${encodeURIComponent(t)}`;
}
