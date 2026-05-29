---
name: deploy-prod-all
description: Full deploy (backend + frontend) to PROD with snapshot+rollback. Requires "DEPLOY PROD" confirmation.
---

# Deploy backend + frontend → PROD

## Pre-conditions

- PROD is provisioned and live; `scripts/deploy/prod/env.sh` is configured
  (DOMAIN=kisschool.in, SSH_KEY=`~/.ssh/enamfoss_prod`).
- `~/.ssh/enamfoss_prod` available.
- `git status` clean (do not silently bypass).
- A recent prod DB backup exists (`bash scripts/deploy/prod/backup-db.sh`) — recommended before any schema-changing release.

## Action

```bash
bash scripts/deploy/prod/deploy-all.sh
```

User must type **`DEPLOY PROD`** at the prompt. Note: `deploy-all` ships backend +
frontend (the SPA at `/admin/`). The public marketing site at `/` is a separate
deploy — run `/deploy-prod-public-site` for it.

## After running

- Confirm `https://kisschool.in/admin/` loads (staff portal, root-mounted).
- Confirm `https://kisschool.in/api/health` returns `{"status":"ok"}` (the deploy's
  own health check already gates on this and auto-rolls-back on failure).
- Watch `journalctl -u school-management -f` for the first minute.
