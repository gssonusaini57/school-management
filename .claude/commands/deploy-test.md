---
name: deploy-test
description: Deploy the FastAPI backend to the TEST server (104.237.5.113). Snapshots before deploy, rolls back automatically if the health check fails.
---

# Deploy backend → TEST

## Action

```bash
bash scripts/deploy/test/deploy-backend.sh
```

## Pre-flight (do these before invoking)

- `git status` — warn if dirty (do **not** block).
- `git rev-parse --abbrev-ref HEAD` — warn if not `master`.
- Show the user the current local backend commit: `git log --oneline -1 -- backend/`.

## What the script does

1. SSH preflight against `104.237.5.113` (key `~/.ssh/uploadmytds_test`).
2. Local AST-parse all `backend/**/*.py` (fail fast on syntax errors).
3. Remote pre-deploy snapshot (`tar` of `/opt/school-management/app/` + `mysqldump`).
4. `rsync` `backend/` → `/opt/school-management/app/` (excludes `.venv`, `__pycache__`).
5. Remote: `pip install -r requirements.txt` + `alembic upgrade head` + `systemctl restart school-management`.
6. Health check: `curl https://expressonly.in/school/api/health` (8 × 5s).
7. On failure: auto-rollback from the snapshot.

## After running

If exit 0:
- Print `https://expressonly.in/school/api/health` response.
- Print last 20 lines of `journalctl -u school-management -n 20 --no-pager`.

If exit non-zero:
- Identify which step failed from the script output.
- Fetch `/opt/school-management/logs/error.log` tail and journal tail.
- Suggest `/clean-logs`, `/rollback` (manual), or inspecting the error.

## Server

- **IP:** `104.237.5.113`
- **SSH key:** `~/.ssh/uploadmytds_test`
- **Domain:** `expressonly.in/school/`
