---
name: deploy-test-all
description: Full deploy (backend + frontend) to the TEST instance (http://69.62.72.137/kisschool/), with snapshot + rollback. The everyday "ship it" command.
---

# Deploy backend + frontend → TEST

## Action

```bash
bash scripts/deploy/test/deploy-all.sh
```

Ships the **working tree**. To ship only committed code while the tree is dirty:

```bash
SRC_ROOT=$(mktemp -d) && git archive HEAD backend frontend packages | tar -x -C "$SRC_ROOT" \
  && SRC_ROOT="$SRC_ROOT" bash scripts/deploy/test/deploy-all.sh
```

## Pre-flight

- `git status` — warn if dirty (do not block); state which tree ships.

## What the script does

1. SSH preflight.
2. AST-parse `backend/**/*.py`.
3. `npm ci && npm run build` (Vite base `/kisschool/admin/`, API `/kisschool/api`).
4. Remote snapshot (`tar app` + `mysqldump school_management_test`).
5. `rsync backend/` and `rsync frontend/dist/` (downloads/ excluded) → `/opt/school-management-test/…`;
   then publishes the local **staging** APK (`kis-attendance-test.apk`) as `downloads/kis-attendance.apk`
   + `app-version-test.json` — never the prod flavour, never deletes.
6. `pip install` + `alembic upgrade head` + `systemctl restart school-management-test`.
7. Health check `http://69.62.72.137/kisschool/api/health` (8 × 5s).
8. Auto-rollback on failure.

## After running

If exit 0:
- Visit `http://69.62.72.137/kisschool/admin/` — logins are prod's (the DB is a prod clone).

If exit non-zero:
- Auto-rollback already ran. Show the failure step + `bash scripts/deploy/test/check-logs.sh 30m`.

## Server

- **IP:** `69.62.72.137` · **SSH key:** `~/.ssh/enamfoss_prod`
- **URL:** `http://69.62.72.137/kisschool/admin/`
