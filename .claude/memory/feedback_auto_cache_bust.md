---
name: feedback-auto-cache-bust
description: Vite injects __BUILD_ID__ + emits version.json; useVersionCheck() polls every 5 min and reloads with ?_v=<ts> on mismatch. nginx no-cache for index.html + version.json. No hard-refresh needed after deploys.
metadata:
  type: feedback
---

After deploys the SPA auto-reloads stale tabs without needing a hard refresh. This was specifically requested by the user in Session 13: "if I am doing any new deployment why I need to hard refesh, handle some version mean then deploy script run then they changes version, if browser diff version found auto clean, handle first time version scenario also".

**Why:** hashed Vite assets bust themselves, but cached `index.html` keeps referencing the OLD hashes — that's the "need a hard refresh after deploy" loop teachers hit. Without explicit handling, every deploy created support friction.

**How to apply:**
- The mechanism is wired by default for every Vite build. `BUILD_ID` is generated in [vite.config.ts](frontend/vite.config.ts) (or overridden via `VITE_BUILD_ID` env), injected as `__BUILD_ID__` via `define`, and emitted to `dist/version.json` by an inline plugin. The runtime hook is [lib/version.ts](frontend/src/lib/version.ts) → `useVersionCheck()`, called once from [App.tsx](frontend/src/App.tsx).
- **Critical:** use `define: { __BUILD_ID__: JSON.stringify(buildId) }` (not raw string) or the substituted token is unquoted and the bundle fails to parse.
- **Critical:** the reload uses `?_v=<ts>` query-bust (`window.location.replace`), not plain `reload()`. Plain reload respects the cached HTML; the query-bust forces a fresh URL fetch which the browser hasn't cached.
- nginx side: [deploy/nginx.school.conf](deploy/nginx.school.conf) sends `Cache-Control: no-cache, must-revalidate` for `/school/admin/`, `index.html`, `version.json`. After editing the conf, push via `scp deploy/nginx.school.conf root@<server>:/etc/nginx/snippets/school.conf && nginx -t && systemctl reload nginx` (auto-classifier may require user authorisation; the conf is also re-pushed by `bash scripts/provision/06-install-nginx-snippet.sh`).
- The Vite dev server uses `BUILD_ID = "dev"`; `useVersionCheck` no-ops in that mode (no version.json poll, no reload).
- Polling cadence: every 5 minutes while document is `visibilityState === "visible"`. Tab-switch fires an immediate check.
