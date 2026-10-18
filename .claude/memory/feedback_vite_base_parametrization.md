---
name: feedback_vite_base_parametrization
description: How the SPA/public-site base path is made build-time configurable so one source deploys to both TEST (/kisschool/ on the bare IP) and PROD (root)
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ef13f4d1-04c7-4142-92f5-05bda9964d1f
---

To serve the same source tree at different URL bases per environment (TEST `/kisschool/admin/`, PROD `/admin/`), the base is **build-time parametrized**, not hardcoded.

**Why:** PROD (kisschool.in) serves at the apex root; TEST (since 2026-10-19 a second instance on the same box, http://69.62.72.137) lives under `/kisschool/`. Breaking either is unacceptable; defaults match TEST, and `scripts/deploy/<env>/env.sh` always exports the real values.

**How to apply:**
- `frontend/vite.config.ts`: `const BASE = process.env.VITE_BASE ?? "/kisschool/admin/"`. Everything downstream derives from `import.meta.env.BASE_URL` (router basename in `main.tsx`, `version.ts` poll URL, `api.ts` LOGIN_PATH, MobileApps APK url) — flip one knob, the whole SPA follows.
- `VITE_API_URL` is read from env; a **shell-exported** `VITE_API_URL` overrides `.env.production` (Vite gives already-present env vars precedence). No `.env` edits needed.
- Favicon in `index.html` must be base-absolute, not relative (a relative path 404s on SPA deep links). Use a `%BASE_URL%crest-mark.png` placeholder substituted by a tiny `transformIndexHtml` plugin in vite.config.ts.
- `public-site/src/_data/site.cjs`: `const basePath = process.env.SITE_BASE_PATH ?? ""` (PROD-only site at the root; `??` honours an explicit value).
- `scripts/deploy/<env>/env.sh` derives everything from one `URL_PREFIX` (`/kisschool` | `""`): `VITE_BASE`, `VITE_API_URL`, `HEALTH_PATH`, `SITE_URL_PATH`, `DOWNLOADS_URL`; `BASE_URL` carries scheme+host (`http://69.62.72.137` | `https://kisschool.in`). `lib.sh` requires them (no `/school` fallbacks) and health-checks `${BASE_URL}${HEALTH_PATH}`. See [[project_test_instance_on_prod_box]].

**Critical gotcha:** `frontend/vite.config.js` is a **committed `tsc` artifact** of `vite.config.ts`, and Vite prefers `.js` over `.ts`. `npm run build` = `tsc -b && vite build` regenerates it, so edits to `.ts` propagate — but a bare `npx vite build` uses the STALE `.js`. Always build via `npm run build`. Verify a build with `grep -r '/kisschool' dist/` → expect hits only for TEST builds. To **typecheck only** (no build), run `npx tsc -b` — `npx tsc -b --noEmit` fails on this repo's project-references setup with `TS6310: Referenced project 'tsconfig.node.json' may not disable emit`.
