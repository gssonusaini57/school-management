---
name: deploy-test-frontend
description: Build the Vite React app and deploy frontend/dist/ to the TEST server (104.237.5.113).
---

# Deploy frontend → TEST

## Action

```bash
bash scripts/deploy/test/deploy-frontend.sh
```

## Pre-flight

- `git status` for `frontend/` — warn if dirty.
- Confirm `frontend/package.json` and `frontend/vite.config.ts` exist.

## What the script does

1. SSH preflight.
2. Local: `npm ci && npm run build` (Vite, base `/school/`, output `frontend/dist/`).
3. `rsync --delete frontend/dist/` → `/opt/school-management/frontend/dist/`.
4. `chown -R school:school /opt/school-management/frontend`.
5. nginx already serves the path — no restart needed.

## After running

If exit 0:
- `curl -sI https://expressonly.in/school/` → expect 200.
- `curl -s https://expressonly.in/school/ | grep -q '<div id="root">'` to confirm SPA shell.

If exit non-zero:
- If `npm run build` failed, surface the TS errors.
- If `rsync` failed, show the SSH error.

## Server

- **IP:** `104.237.5.113`
- **SSH key:** `~/.ssh/uploadmytds_test`
- **URL:** `https://expressonly.in/school/`
