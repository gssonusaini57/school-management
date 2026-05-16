---
name: provision-test
description: One-time provisioning of the TEST server (104.237.5.113) — installs python3.12, creates `school` system user, /opt/school-management tree, MySQL DB+user, /etc/systemd/system/school-management.service, /etc/nginx/snippets/school.conf. Idempotent.
---

# Provision the TEST server

## Action

Run a read-only inspection first, then (after user `y` confirmation) run the full provisioning.

```bash
bash scripts/provision/provision.sh --inspect-only
```

If the inspection looks correct, run:

```bash
bash scripts/provision/provision.sh
```

## Server

- **IP:** `104.237.5.113`
- **SSH key:** `~/.ssh/uploadmytds_test`
- **Domain:** `expressonly.in` (path `/school/`)

## Pre-conditions to verify before invoking

- `~/.ssh/uploadmytds_test` exists and is reachable (`ssh -i ~/.ssh/uploadmytds_test root@104.237.5.113 echo ok`)
- We are at the repo root (`pwd` ends with `/school-management`)
- `deploy/school-management.service` and `deploy/nginx.school.conf` both exist

## After running

- Show the user the summary block from the script (id school / dir listing / .env stat / mysql databases / nginx -t).
- Tell the user the next step is `/deploy-test-all` (or `bash scripts/deploy/test/deploy-all.sh`).
- Do **not** start `school-management.service` here — that happens during the first deploy when code+venv exist.

## If something fails

- `nginx -t` failure → restore the `*.bak.*` from step 06, ask user to inspect.
- MySQL root auth failure → ask user how they currently access MySQL as root (socket / `/root/.my.cnf`); script needs one of those.
- Re-running is safe (every step is idempotent).
