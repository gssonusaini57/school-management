import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AcademicSession } from "@/types/api";

/** Session containing `today` under the April→March school year, e.g. Feb 2027 → "2026-27". */
export function defaultSessionName(today: Date = new Date()): string {
  const y = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
  return `${y}-${String((y + 1) % 100).padStart(2, "0")}`;
}

/** Every configured academic session, newest first (GET /sessions). */
export function useSessions() {
  return useQuery<AcademicSession[]>({
    queryKey: ["sessions"],
    queryFn: () => api.get("/sessions").then((r) => r.data),
    staleTime: 5 * 60_000,
  });
}

/** `d` as YYYY-MM-DD on the local calendar (the school and its staff are on IST), not UTC's. */
function localIsoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/**
 * The current session as the server picks it (services/sessions.current_session):
 * the one flagged current, else the one whose dates contain today. Never simply the
 * newest: early in a new school year that would file new marks under last year.
 */
export function currentSessionRow(
  sessions: AcademicSession[] | undefined,
  today: Date = new Date(),
): AcademicSession | undefined {
  const flagged = sessions?.find((s) => s.is_current);
  if (flagged) return flagged;
  const day = localIsoDate(today);
  return sessions?.find(
    (s) => !!s.starts_on && !!s.ends_on && s.starts_on.slice(0, 10) <= day && day <= s.ends_on.slice(0, 10),
  );
}

/** The server's current session; the April-rollover guess while loading or when none covers today. */
export function useCurrentSessionName(): string {
  const { data } = useSessions();
  return currentSessionRow(data)?.session ?? defaultSessionName();
}
