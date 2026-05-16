# Session 4 — 2026-05-07 (late) · Production deploy + reusable infra

**Focus:** Provision the test VPS, build reusable provision/deploy scripts mirroring uploadmytds, ship to https://expressonly.in/school/.

## What was created (all idempotent / re-runnable)
- [scripts/provision/](../scripts/provision/) — 8 numbered scripts (`00-common.sh` shared lib, `01-install-prereqs.sh`, `02-create-user-dirs.sh`, `03-create-mysql-db.sh`, `04-write-env.sh`, `05-install-systemd.sh`, `06-install-nginx-snippet.sh`, `provision.sh` wrapper). Pre-flight inspection, then `y` confirmation, then run.
- [scripts/deploy/common/lib.sh](../scripts/deploy/common/lib.sh) — shared helpers: `ssh_run`, `scp_up/_down`, `health_wait`, `remote_snapshot`, `remote_rollback`, `local_python_lint`, `local_frontend_build`, `push_backend/_frontend`, `remote_install_and_restart`, `deploy_full/_backend_only/_frontend_only`.
- [scripts/deploy/test/](../scripts/deploy/test/) — `env.sh` (defaults), `deploy-backend.sh`, `deploy-frontend.sh`, `deploy-all.sh`, `download-logs.sh`, `backup-db.sh`, `rollback.sh`.
- [scripts/deploy/prod/](../scripts/deploy/prod/) — symmetric set with `CHANGE_ME_*` guards in `env.sh` that refuse to run until configured. Each prod script requires typing `DEPLOY PROD` to confirm.
- [.claude/commands/](./commands/) — 8 slash commands (`provision-test`, `deploy-test`, `deploy-test-frontend`, `deploy-test-all`, `deploy-prod*`, `clean-logs`).
- [scripts/README.md](../scripts/README.md) — one-page deploy cheatsheet.

## Deploy outcome
- Provisioning: `bash scripts/provision/provision.sh` ran end-to-end on `104.237.5.113` — installed prereqs, created `school` user, `/opt/school-management/` tree, `school_management` DB + `school` user, `.env` (secrets generated on server), systemd unit enabled, nginx snippet installed.
- First deploy: `bash scripts/deploy/test/deploy-all.sh` — alembic created baseline schema, gunicorn started, health check 200.
- Bugs found + fixed in-flight: (a) MySQL root needed password (sourced from uploadmytds's mysql-install.sh after explicit user authorization); (b) nginx `}server {` same-line boundary tricked the awk-based include inserter — replaced with Python brace-depth parser; (c) `/opt/school-management/` mode 750 blocked nginx (www-data) — fixed to 755; (d) nested `location` with `alias` for asset cache headers caused 404 — simplified the snippet to a flat `location /school/`. Fixes propagated back to repo so re-running on a fresh server now works first try.

## Live URLs verified
- `https://expressonly.in/school/` → 200, React SPA shell
- `https://expressonly.in/school/api/health` → `{"status":"ok"}`
- `https://expressonly.in/school/api/auth/login` (admin/admin123) → JWT issued
- `https://expressonly.in/school/assets/index-*.js|.css` → 200 from disk
