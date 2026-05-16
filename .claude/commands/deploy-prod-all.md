---
name: deploy-prod-all
description: Full deploy (backend + frontend) to PROD with snapshot+rollback. Requires "DEPLOY PROD" confirmation.
---

# Deploy backend + frontend → PROD

## Pre-conditions

- `scripts/deploy/prod/env.sh` configured.
- `~/.ssh/school-management_prod` available.
- Provisioning has been run on the prod server.
- `git status` clean (do not silently bypass).
- A recent prod DB backup exists (`bash scripts/deploy/prod/backup-db.sh`) — recommended before any schema-changing release.

## Action

```bash
bash scripts/deploy/prod/deploy-all.sh
```

User must type **`DEPLOY PROD`** at the prompt.

## After running

- Confirm `<DOMAIN>/school/` loads.
- Confirm `<DOMAIN>/school/api/health` returns `{"status":"ok"}`.
- Watch `journalctl -u school-management -f` for the first minute.
