/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Injected by vite.config.ts via `define`. Used by the cache-bust check
// (see lib/version.ts) to detect when the deployed bundle has changed.
declare const __BUILD_ID__: string;
