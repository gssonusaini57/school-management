---
name: deploy-test
description: Deploy the FastAPI backend to the TEST instance (http://69.62.72.137/kisschool/, second instance on the prod box). Snapshots before deploy, rolls back automatically if the health check fails.
---

# Deploy backend → TEST

## Action

```bash
bash scripts/deploy/test/deploy-backend.sh
```

Deploys the **working tree**. To ship only committed code while the tree holds unfinished
work (e.g. another session's), deploy a clean export instead:

```bash
SRC_ROOT=$(mktemp -d) && git archive HEAD backend frontend packages | tar -x -C "$SRC_ROOT" \
  && SRC_ROOT="$SRC_ROOT" bash scripts/deploy/test/deploy-backend.sh
```

## Pre-flight (do these before invoking)

- `git status` — warn if dirty (do **not** block); say whether the working tree or HEAD ships.
- Show the user the current local backend commit: `git log --oneline -1 -- backend/`.

## What the script does

1. SSH preflight against `69.62.72.137` (key `~/.ssh/enamfoss_prod`).
2. Local AST-parse all `backend/**/*.py`.
3. Remote snapshot (`tar` of `/opt/school-management-test/app/` + `mysqldump school_management_test`).
4. `rsync` `backend/` → `/opt/school-management-test/app/`.
5. Remote: `pip install -r requirements.txt` + `alembic upgrade head` + `systemctl restart school-management-test`.
6. Health check: `curl http://69.62.72.137/kisschool/api/health` (8 × 5s).
7. On failure: auto-rollback from the snapshot.

## After running

If exit 0:
- Print the `http://69.62.72.137/kisschool/api/health` response.
- `bash scripts/deploy/test/check-logs.sh 15m` for a quick look.

If exit non-zero:
- Identify which step failed; `bash scripts/deploy/test/check-logs.sh 30m`.

## Server

- **IP:** `69.62.72.137` (shared with PROD + enamfoss) · **SSH key:** `~/.ssh/enamfoss_prod`
- **Instance:** `/opt/school-management-test`, unit `school-management-test`, gunicorn `127.0.0.1:8001`, DB `school_management_test`
- **URL:** `http://69.62.72.137/kisschool/` (plain HTTP)
