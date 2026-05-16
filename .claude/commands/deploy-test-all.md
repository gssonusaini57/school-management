---
name: deploy-test-all
description: Full deploy (backend + frontend) to the TEST server, with snapshot + rollback. The everyday "ship it" command.
---

# Deploy backend + frontend → TEST

## Action

```bash
bash scripts/deploy/test/deploy-all.sh
```

## Pre-flight

- `git status` — warn if dirty (do not block).
- Confirm both `backend/` and `frontend/` are present.

## What the script does

1. SSH preflight.
2. AST-parse `backend/**/*.py`.
3. `npm ci && npm run build` for frontend.
4. Remote pre-deploy snapshot (`tar app + mysqldump`).
5. `rsync backend/` and `rsync frontend/dist/`.
6. `pip install` + `alembic upgrade head` + `systemctl restart school-management`.
7. Health check `https://expressonly.in/school/api/health` (8 × 5s).
8. Auto-rollback on failure.

## After running

If exit 0:
- Visit `https://expressonly.in/school/` and confirm SPA loads.
- Suggest the user log in as `admin` / `admin123` and test one happy path (add a student).

If exit non-zero:
- Auto-rollback already ran. Show the failure step + journal tail.

## Server

- **IP:** `104.237.5.113`
- **SSH key:** `~/.ssh/uploadmytds_test`
- **URL:** `https://expressonly.in/school/`
