---
name: deploy-test-frontend
description: Build the Vite React app and deploy frontend/dist/ to the TEST instance (http://69.62.72.137/kisschool/admin/).
---

# Deploy frontend → TEST

## Action

```bash
bash scripts/deploy/test/deploy-frontend.sh
```

(Prefix `SRC_ROOT=<clean export>` to ship committed code only — see `/deploy-test-all`.)

## Pre-flight

- `git status` for `frontend/` — warn if dirty.

## What the script does

1. SSH preflight.
2. Local: `npm ci && npm run build` (Vite, base `/kisschool/admin/`, output `frontend/dist/`).
3. `rsync --delete frontend/dist/` (excluding `downloads/`) → `/opt/school-management-test/frontend/dist/`,
   then publishes the staging APK + `app-version-test.json` if built locally.
4. `chown -R school-test:school-test /opt/school-management-test/frontend`.
5. nginx already serves the path — no restart needed.

## After running

If exit 0:
- `curl -sI http://69.62.72.137/kisschool/admin/` → expect 200 + `Cache-Control: no-cache, must-revalidate`.
- `curl -s http://69.62.72.137/kisschool/admin/ | grep -q '<div id="root">'` to confirm the SPA shell.

If exit non-zero:
- If `npm run build` failed, surface the TS errors.
- If `rsync` failed, show the SSH error.

## Server

- **IP:** `69.62.72.137` · **SSH key:** `~/.ssh/enamfoss_prod`
- **URL:** `http://69.62.72.137/kisschool/admin/`
