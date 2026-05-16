---
name: deploy-prod-frontend
description: Build and deploy frontend to PROD. Requires "DEPLOY PROD" confirmation.
---

# Deploy frontend → PROD

## Pre-conditions

- `scripts/deploy/prod/env.sh` configured (no CHANGE_ME placeholders).
- `~/.ssh/school-management_prod` available.
- Provisioning has been run on prod server.
- `git status` clean.

## Action

```bash
bash scripts/deploy/prod/deploy-frontend.sh
```

User must type **`DEPLOY PROD`** at the prompt.

## After running

- `curl -sI <DOMAIN>/school/` → expect 200.
- Visually confirm the SPA loads.
