import { useCallback, useEffect, useState } from "react";

export type NavMode = "topbar" | "sidebar";

const STORAGE_KEY = "kis.nav.mode";
const DEFAULT_MODE: NavMode = "topbar";

function readStoredMode(): NavMode {
  if (typeof window === "undefined") return DEFAULT_MODE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw === "sidebar" || raw === "topbar" ? raw : DEFAULT_MODE;
  } catch {
    return DEFAULT_MODE;
  }
}

export function useNavMode() {
  const [mode, setModeState] = useState<NavMode>(readStoredMode);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // localStorage may be disabled (private mode); silently ignore.
    }
  }, [mode]);

  const setMode = useCallback((next: NavMode) => setModeState(next), []);
  const toggle = useCallback(
    () => setModeState((m) => (m === "topbar" ? "sidebar" : "topbar")),
    [],
  );

  return { mode, setMode, toggle };
}
