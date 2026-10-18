---
name: provision-test
description: One-time, idempotent provisioning of the TEST instance — a second copy of the app on the PROD box 69.62.72.137, served at http://69.62.72.137/kisschool/ (own user school-test, /opt/school-management-test, MySQL school_management_test, unit school-management-test on :8001, nginx snippet included from the enamfoss bare-IP vhost).
---

# Provision the TEST instance

Everything (server, key, paths, user, unit, port, DB, nginx snippet) comes from
`scripts/deploy/test/env.sh`; nothing needs exporting.

## Action

1. Read-only inspection (always safe):
   ```bash
   bash scripts/provision/provision.sh --inspect-only
   ```
2. Show the user the inspection and confirm: port **8001 free**, the include target is
   **`/etc/nginx/conf.d/enamfoss.conf`** (the `server_name 69.62.72.137` block), and nothing
   unexpected already exists under `/opt/school-management-test`.
3. After the user says go (Claude's shell has no TTY, so pass the confirmation through):
   ```bash
   ASSUME_YES=1 bash scripts/provision/provision.sh
   ```

MySQL admin access for step 03: `MYSQL_ROOT_PASSWORD` if exported, otherwise the server's
own maintenance account `/etc/mysql/debian.cnf` (root-only, used in place on the server),
otherwise a hidden prompt. Never type the root password into chat.

## What it creates (PROD on the same box is not touched)

| Step | Result |
|---|---|
| 01 | prereqs (python3.12, WeasyPrint libs, fonts) — already present on this box |
| 02 | system user `school-test`, `/opt/school-management-test/{app,frontend/dist,logs,backups}` (backups 700) |
| 03 | DB `school_management_test` + user `school_test` (grants on that DB only), `.db_password`, `.my.cnf` |
| 04 | `.env` — fresh JWT secret, `APP_BASE_URL=http://69.62.72.137/kisschool/admin`, **no SMTP keys** (email off on TEST) |
| 05 | `/etc/systemd/system/school-management-test.service` (gunicorn 127.0.0.1:8001), enabled, not started |
| 06 | `/etc/nginx/snippets/school-management-test.conf` + ONE `include` line in `enamfoss.conf` (backup in `/etc/nginx/backups/`, `nginx -t` gated, auto-restored on failure) |

## After running

- Next: `/deploy-test-all`, then `/sync-test-data` to clone prod data.
- Do **not** start the service here — the first deploy installs the venv and starts it.

## If something fails

- Every step is idempotent; re-run after fixing the cause.
- Step 03 exit 4 = the MySQL user exists but this instance didn't create it — pick another `DB_USER`.
- Step 06 `nginx -t` failure restores the backups automatically; inspect `/etc/nginx/backups/`.
- Full removal: `systemctl disable --now school-management-test; rm /etc/systemd/system/school-management-test.service; systemctl daemon-reload`; restore `enamfoss.conf` from `/etc/nginx/backups/` (or delete the include line), `rm /etc/nginx/snippets/school-management-test.conf; nginx -t && systemctl reload nginx`; `DROP DATABASE school_management_test; DROP USER 'school_test'@'localhost';`; `rm -rf /opt/school-management-test; userdel school-test`.
