import { useEffect, useRef } from "react";

/**
 * Cache-bust check.
 *
 * Every Vite build embeds a unique `__BUILD_ID__` into the bundle (see
 * vite.config.ts) and emits `dist/version.json` containing the same id. On
 * deploy, the new dist is served at `/school/admin/`. Existing users keep
 * running the OLD bundle out of browser cache — that's the "need a hard
 * refresh" problem.
 *
 * `useVersionCheck()` fixes it: on mount and every 5 minutes (while the tab
 * is visible), it fetches `version.json` with `cache: 'no-store'` and
 * compares the server id with `BUILD_ID`. On mismatch it reloads with a
 * cache-busting query (`?_v=<ts>`) so the cached `index.html` is bypassed
 * and the browser fetches the new shell + new hashed assets.
 *
 * First-time visits are a no-op: the freshly-fetched HTML references the
 * matching bundle, so embedded === server.
 */

export const BUILD_ID: string =
  typeof __BUILD_ID__ === "string" && __BUILD_ID__ ? __BUILD_ID__ : "dev";

// `BASE_URL` is "/school/admin/" in prod, "/" in dev — match the SPA mount.
const VERSION_URL = `${import.meta.env.BASE_URL.replace(/\/?$/, "/")}version.json`;

const POLL_MS = 5 * 60 * 1000;

interface VersionFile { build_id?: string }

async function fetchServerBuildId(signal?: AbortSignal): Promise<string | null> {
  try {
    const res = await fetch(`${VERSION_URL}?t=${Date.now()}`, {
      cache: "no-store",
      credentials: "omit",
      signal,
    });
    if (!res.ok) return null;
    const json = (await res.json()) as VersionFile;
    return typeof json.build_id === "string" ? json.build_id : null;
  } catch {
    return null;
  }
}

function reloadWithCacheBust(): void {
  // A query-bust ensures the browser fetches a fresh HTML even if nginx /
  // upstream caches haven't expired index.html. The new HTML references
  // new hashed JS/CSS, so subsequent loads naturally cache-bust themselves.
  const url = new URL(window.location.href);
  url.searchParams.set("_v", String(Date.now()));
  // Use `replace` so the busted URL doesn't pollute history.
  window.location.replace(url.toString());
}

let triggered = false;

export async function checkBuildOnce(): Promise<void> {
  if (triggered) return;
  if (BUILD_ID === "dev") return; // skip in vite dev server
  const server = await fetchServerBuildId();
  if (server && server !== BUILD_ID) {
    triggered = true;
    reloadWithCacheBust();
  }
}

export function useVersionCheck(): void {
  const interval = useRef<number | null>(null);

  useEffect(() => {
    if (BUILD_ID === "dev") return; // no version.json in `vite dev`
    let cancelled = false;

    void checkBuildOnce();

    const tick = () => {
      if (cancelled) return;
      if (document.visibilityState !== "visible") return;
      void checkBuildOnce();
    };

    interval.current = window.setInterval(tick, POLL_MS);
    document.addEventListener("visibilitychange", tick);

    return () => {
      cancelled = true;
      if (interval.current) window.clearInterval(interval.current);
      document.removeEventListener("visibilitychange", tick);
    };
  }, []);
}
