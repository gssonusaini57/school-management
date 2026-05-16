---
name: deploy-prod
description: Deploy backend to PROD. Requires explicit "DEPLOY PROD" confirmation. PROD env.sh must be configured first.
---

# Deploy backend → PROD

## Pre-conditions (verify before invoking)

- `scripts/deploy/prod/env.sh` has been edited (no `CHANGE_ME_*` placeholders).
- `~/.ssh/school-management_prod` exists and is in the prod server's `authorized_keys`.
- `scripts/provision/provision.sh` has been run against the prod server (`SERVER=… SSH_KEY=… DOMAIN=… bash scripts/provision/provision.sh`).
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
- Print `<DOMAIN>/school/api/health` response.
- Print `journalctl -u school-management -n 20`.

If exit non-zero:
- Auto-rollback already happened. Surface the failing step + journal tail.
- Page the on-call human if you have one.
