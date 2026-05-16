---
name: Slash commands inventory for school-management
description: 11 slash commands under .claude/commands/ — provision-test, deploy-test, deploy-test-frontend, deploy-test-all, deploy-test-public-site, deploy-prod, deploy-prod-frontend, deploy-prod-all, clean-logs, release-android, check-logs.
type: reference
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
Project-local slash commands at `.claude/commands/`:

| Command | Script | Purpose |
|---|---|---|
| `/provision-test` | `scripts/provision/provision.sh` | One-time TEST server bootstrap (idempotent: prereqs / school user / dirs / MySQL DB+user / .env / systemd unit / nginx snippet) |
| `/deploy-test` | `scripts/deploy/test/deploy-backend.sh` | Backend-only deploy to TEST |
| `/deploy-test-frontend` | `scripts/deploy/test/deploy-frontend.sh` | Frontend-only (Vite build + rsync) |
| `/deploy-test-all` | `scripts/deploy/test/deploy-all.sh` | Backend + frontend with snapshot + auto-rollback |
| `/deploy-prod` | `scripts/deploy/prod/deploy-backend.sh` | PROD backend; requires typing `DEPLOY PROD` |
| `/deploy-prod-frontend` | `scripts/deploy/prod/deploy-frontend.sh` | PROD frontend; requires typing `DEPLOY PROD` |
| `/deploy-prod-all` | `scripts/deploy/prod/deploy-all.sh` | PROD full deploy; requires typing `DEPLOY PROD` |
| `/clean-logs` | local `rm -rf logs_backup_*` | Clean local log-backup dirs (after explicit y) |
| `/release-android` | `scripts/build-android.sh` + frontend deploy (gated by y/N) | Build a fresh signed APK, then ask before publishing it via the frontend deploy |
| `/check-logs` (Session 9) | `scripts/deploy/{test,prod}/check-logs.sh` | Read-only SSH log streamer: 6 sections (status / journalctl / error.log / tracebacks / access.log / 4xx-5xx). Shorthand windows `30m` / `2h` / `1d`. Default 1h |
| `/deploy-test-public-site` | `scripts/deploy/test/deploy-public-site.sh` | Eleventy + Tailwind CLI build → rsync to nginx `/school/` |

Each command's markdown spec describes pre-flight checks, what to run, and what to verify after.

**Other manual scripts** (not slash commands but reusable):
- `scripts/deploy/test/download-logs.sh` — pull `/opt/school-management/logs/` + journalctl tail
- `scripts/deploy/test/backup-db.sh` — fresh mysqldump → `~/Downloads/db-backups/`
- `scripts/deploy/test/rollback.sh [<timestamp>]` — list snapshots / restore one
- Same set under `scripts/deploy/prod/`.

**How to apply:** When the user types one of these slash commands, follow the markdown spec exactly. The pre-flight and post-deploy verification steps are not optional.
