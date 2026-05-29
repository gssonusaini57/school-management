---
name: deploy-prod
description: Deploy backend to PROD. Requires explicit "DEPLOY PROD" confirmation. PROD env.sh must be configured first.
---

# Deploy backend → PROD

## Pre-conditions (verify before invoking)

- PROD is already provisioned and live: `scripts/deploy/prod/env.sh` is configured
  (SERVER=69.62.72.137, DOMAIN=kisschool.in, SSH_KEY=`~/.ssh/enamfoss_prod`).
- `~/.ssh/enamfoss_prod` exists and is in the prod server's `authorized_keys`.
- `git status` is clean. Warn loudly if not — do **not** silently proceed.
- Confirm we are on `master` (or whatever release branch).

## Action

```bash
bash scripts/deploy/prod/deploy-backend.sh
```

The script asks the user to type **`DEPLOY PROD`** at the prompt before continuing.

## Behavior

Identical code path to `deploy-test`: snapshot → rsync → pip → alembic → restart → health → auto-rollback.

## After running

If exit 0:
- Print `https://kisschool.in/api/health` response (prod serves the API at the root,
  not under `/school/`; the deploy script's own health check already covers this).
- Print `journalctl -u school-management -n 20`.

If exit non-zero:
- Auto-rollback already happened. Surface the failing step + journal tail.
- Page the on-call human if you have one.
