import { useEffect, useRef } from "react";
import { useQueryClient, type QueryKey } from "@tanstack/react-query";
import { refreshSession } from "./api";
import { getToken, useToken } from "./auth";

const baseURL = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

/**
 * Reopen a stream the server refused after 2 s, then 4, 8, 16, 32 s — at most
 * MAX_REOPENS times in a row (about a minute: long enough to ride out a deploy's
 * restart), then stop until the stream opens again or the token changes.
 */
const REOPEN_DELAY_MS = 2_000;
const MAX_REOPENS = 5;

/**
 * Subscribe to a server-sent-events channel; every message invalidates `invalidateKeys`.
 *
 * The JWT rides in the URL (EventSource can't set headers) and is read through
 * useToken(), so a refreshed token reopens the stream with the new one. A dropped
 * connection the browser is still retrying itself (readyState CONNECTING) is left
 * alone; one the server refused (CLOSED — an expired token answers 401, a restart
 * 502/503) gets a refresh attempt and is reopened with a backoff. The attempt
 * count survives the effect re-running on a new token, so a stream failing for any
 * other reason can't turn into an endless refresh → reopen loop.
 */
export function useSSE(channel: string, invalidateKeys: QueryKey[]) {
  const qc = useQueryClient();
  const token = useToken();
  const keysJson = JSON.stringify(invalidateKeys);
  const reopens = useRef(0);

  useEffect(() => {
    if (!token) return;
    const keys = JSON.parse(keysJson) as QueryKey[];
    let es: EventSource | null = null;
    let timer: number | undefined;
    let disposed = false;

    const open = () => {
      if (disposed) return;
      es = new EventSource(`${baseURL}/stream/${channel}?token=${encodeURIComponent(getToken())}`);
      es.onopen = () => {
        reopens.current = 0;
      };
      es.onmessage = () => {
        keys.forEach((k) => qc.invalidateQueries({ queryKey: k }));
      };
      es.onerror = () => {
        if (disposed || !es || es.readyState !== EventSource.CLOSED) return;
        es.close();
        es = null;
        if (reopens.current >= MAX_REOPENS) return;
        reopens.current += 1;
        timer = window.setTimeout(
          async () => {
            // A refreshed token re-runs this effect (token dep), which opens the
            // stream itself; otherwise retry with what we have — the server may
            // just have been restarting.
            const before = getToken();
            await refreshSession();
            if (!disposed && getToken() === before) open();
          },
          REOPEN_DELAY_MS * 2 ** (reopens.current - 1),
        );
      };
    };

    open();
    return () => {
      disposed = true;
      window.clearTimeout(timer);
      es?.close();
    };
  }, [channel, keysJson, qc, token]);
}
