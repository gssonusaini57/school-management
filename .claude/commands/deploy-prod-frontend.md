---
name: deploy-prod-frontend
description: Build and deploy frontend to PROD. Requires "DEPLOY PROD" confirmation.
---

# Deploy frontend → PROD

## Pre-conditions

- PROD is provisioned and live; `scripts/deploy/prod/env.sh` is configured
  (DOMAIN=kisschool.in, SSH_KEY=`~/.ssh/enamfoss_prod`, VITE_BASE=`/admin/`,
  VITE_API_URL=`/api`). The build uses these to produce a root-mounted SPA.
- `~/.ssh/enamfoss_prod` available.
- `git status` clean.

## Action

```bash
bash scripts/deploy/prod/deploy-frontend.sh
```

User must type **`DEPLOY PROD`** at the prompt.

## After running

- `curl -sI https://kisschool.in/admin/` → expect 200 (the staff portal SPA;
  prod serves it at `/admin/`, not `/school/admin/`).
- Visually confirm the SPA loads and `https://kisschool.in/admin/version.json`
  returns a fresh build id.
- This also republishes the prod-flavor APK from `frontend/public/downloads/` to
  `/downloads/` (the rsync includes it).
