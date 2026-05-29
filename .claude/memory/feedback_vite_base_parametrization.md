---
name: feedback_vite_base_parametrization
description: How the SPA/public-site base path is made build-time configurable so one source deploys to both TEST (/school/) and PROD (root)
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ef13f4d1-04c7-4142-92f5-05bda9964d1f
---

To serve the same source tree at different URL bases per environment (TEST `/school/admin/`, PROD `/admin/`), the base is **build-time parametrized**, not hardcoded.

**Why:** PROD (kisschool.in, dedicated) serves at the apex root; TEST (expressonly.in, shared) stays under `/school/`. Breaking either is unacceptable, so changes default to the TEST values.

**How to apply:**
- `frontend/vite.config.ts`: `const BASE = process.env.VITE_BASE ?? "/school/admin/"`. Everything downstream derives from `import.meta.env.BASE_URL` (router basename in `main.tsx`, `version.ts` poll URL, `api.ts` LOGIN_PATH, MobileApps APK url) — flip one knob, the whole SPA follows.
- `VITE_API_URL` is read from env; a **shell-exported** `VITE_API_URL` overrides `.env.production` (Vite gives already-present env vars precedence). No `.env` edits needed.
- Favicon in `index.html` must be base-absolute, not relative (a relative path 404s on SPA deep links). Use a `%BASE_URL%crest-mark.png` placeholder substituted by a tiny `transformIndexHtml` plugin in vite.config.ts.
- `public-site/src/_data/site.cjs`: `const basePath = process.env.SITE_BASE_PATH ?? "/school"` (`??` so an explicit `""` for root is honoured).
- `scripts/deploy/common/lib.sh` build steps pass these env vars (with `:-` test defaults; use bare `-` for SITE_BASE_PATH so empty string survives). Health-check + URL strings use `${HEALTH_PATH:-...}` / `${SITE_URL_PATH:-...}`. The per-env values are set in `scripts/deploy/<env>/env.sh`.

**Critical gotcha:** `frontend/vite.config.js` is a **committed `tsc` artifact** of `vite.config.ts`, and Vite prefers `.js` over `.ts`. `npm run build` = `tsc -b && vite build` regenerates it, so edits to `.ts` propagate — but a bare `npx vite build` uses the STALE `.js`. Always build via `npm run build`. Verify a prod build with `grep -r '/school' dist/` → expect none.
