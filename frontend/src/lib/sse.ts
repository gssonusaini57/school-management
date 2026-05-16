import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getToken } from "./api";

const baseURL = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

export function useSSE(channel: string, invalidateKeys: string[][]) {
  const qc = useQueryClient();

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    const es = new EventSource(
      `${baseURL}/stream/${channel}?token=${encodeURIComponent(t)}`
    );
    es.onmessage = () => {
      invalidateKeys.forEach((k) => qc.invalidateQueries({ queryKey: k }));
    };
    es.onerror = () => {
      // EventSource auto-reconnects; no-op
    };
    return () => es.close();
  }, [channel, JSON.stringify(invalidateKeys), qc]);
}
