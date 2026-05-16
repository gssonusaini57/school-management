---
name: SPA mounted on a subpath (/school/) — routing rules
description: This SPA is served at https://expressonly.in/school/, not at root. React Router needs basename, the 401 redirect needs BASE_URL, and nginx try_files must fall back to /school/index.html. Hardcoding any of these to `/` will break routing on hard refresh.
type: feedback
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
The school-management SPA is mounted at `/school/` because it shares the `expressonly.in` domain with `uploadmytds` (which serves `/`, `/app/`, `/api/` for its own purposes). Three pieces have to know about the subpath:

1. **Vite `base: "/school/"`** in [frontend/vite.config.ts](../../../Documents/GitHub/school-management/frontend/vite.config.ts) — emits `<script src="/school/assets/...">` etc. Without it, asset URLs are `/assets/...` and 404 in production.
2. **React Router `basename`** in [frontend/src/main.tsx](../../../Documents/GitHub/school-management/frontend/src/main.tsx) — read from `import.meta.env.BASE_URL` (which Vite sets to whatever `base` is). Without it, `<NavLink to="/admissions">` produces an `<a href="/admissions">` instead of `/school/admissions`, and on hard refresh nginx routes to uploadmytds's catch-all.
3. **API redirect** in [frontend/src/lib/api.ts](../../../Documents/GitHub/school-management/frontend/src/lib/api.ts) — the 401 handler must redirect to `import.meta.env.BASE_URL + "login"`, not hardcoded `/login`.
4. **nginx `try_files`** in [deploy/nginx.school.conf](../../../Documents/GitHub/school-management/deploy/nginx.school.conf) — `try_files $uri $uri/ /school/index.html;` so any `/school/*` URL that doesn't match a file falls back to the SPA shell. This makes hard-refresh on deep URLs (e.g. `/school/students/42`) work.

**The "is the SPA at root or subpath" decision propagates through 4 files.** Encoding it in `import.meta.env.BASE_URL` and reading from there means the same code works for both deployments — if you ever move school-management to its own root domain, just change `vite.config.ts` `base: "/"` and rebuild; everything else follows.

**How to apply:** When you build a similar SPA on this VPS or any other shared-domain setup, mirror this exact pattern. Don't hardcode the prefix anywhere; always read from BASE_URL. And remember the nginx `try_files` clause — it's invisible in dev (Vite handles it) but essential in prod.
