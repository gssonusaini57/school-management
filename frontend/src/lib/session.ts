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

/** The server's current session, falling back to the April-rollover guess while loading. */
export function useCurrentSessionName(): string {
  const { data } = useSessions();
  return data?.find((s) => s.is_current)?.session ?? defaultSessionName();
}
