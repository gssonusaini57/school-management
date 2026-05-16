# Deployment scripts

One-page cheatsheet. Detailed plan: `.claude/plans/create-a-deep-plan-snug-tome.md`.

## Layout

```
scripts/
├── provision/              one-time per-server setup (idempotent)
│   ├── 01-install-prereqs.sh        python3.12, venv, libmysqlclient-dev, curl, rsync
│   ├── 02-create-user-dirs.sh       useradd school + /opt/school-management/{app,frontend/dist,logs,backups}
│   ├── 03-create-mysql-db.sh        CREATE DATABASE/USER/GRANT (idempotent), persists pwd to /opt/school-management/.db_password
│   ├── 04-write-env.sh              writes /opt/school-management/.env (chmod 600 school:school)
│   ├── 05-install-systemd.sh        installs /etc/systemd/system/school-management.service
│   ├── 06-install-nginx-snippet.sh  installs /etc/nginx/snippets/school.conf + include in expressonly.in block
│   └── provision.sh                 wrapper: SSH-inspect + confirm + run 01..06
├── deploy/
│   ├── common/lib.sh                shared: ssh_run/scp_*/health_wait/snapshot/rollback/build/deploy_full
│   ├── test/                        TEST: 104.237.5.113 · expressonly.in · ~/.ssh/uploadmytds_test
│   │   ├── env.sh                   defaults
│   │   ├── deploy-backend.sh        backend only
│   │   ├── deploy-frontend.sh       frontend only
│   │   ├── deploy-all.sh            full (backend + frontend, snapshot, rollback)
│   │   ├── download-logs.sh         scp /opt/school-management/logs + journalctl tail
│   │   ├── backup-db.sh             mysqldump → ~/Downloads/db-backups/school_test_<ts>.sql.gz
│   │   └── rollback.sh              list snapshots / restore one
│   └── prod/                        PROD: edit env.sh first (CHANGE_ME guards refuse to run otherwise)
│       └── (same set of scripts; each prompts "Type 'DEPLOY PROD' to confirm")
└── README.md (this file)
```

## Quick start (test)

```bash
# 1. One-time provisioning (uses ~/.ssh/uploadmytds_test against 104.237.5.113)
bash scripts/provision/provision.sh

# 2. First deploy (and every subsequent deploy)
bash scripts/deploy/test/deploy-all.sh

# 3. Inspect / debug
bash scripts/deploy/test/download-logs.sh
bash scripts/deploy/test/rollback.sh                 # lists snapshots
bash scripts/deploy/test/rollback.sh 20260507_123456 # restore that snapshot
```

## Environment overrides

Every script reads its server-specific values from env vars. Defaults are in
`scripts/deploy/{test,prod}/env.sh`. Override at the call site:

```bash
SCHOOL_TEST_SERVER=10.0.0.5 \
SCHOOL_TEST_SSH_KEY=~/.ssh/another \
bash scripts/deploy/test/deploy-all.sh
```

## Promoting test → prod

```bash
# 1. Edit scripts/deploy/prod/env.sh (replace CHANGE_ME_PROD_IP and CHANGE_ME_PROD_DOMAIN)
$EDITOR scripts/deploy/prod/env.sh

# 2. Generate a dedicated prod SSH key and add to prod authorized_keys
ssh-keygen -t ed25519 -f ~/.ssh/school-management_prod
ssh-copy-id -i ~/.ssh/school-management_prod.pub root@<prod-ip>

# 3. Provision the prod box (same flow as test)
SERVER=<prod-ip> SSH_KEY=~/.ssh/school-management_prod DOMAIN=<prod-domain> \
  bash scripts/provision/provision.sh

# 4. Deploy
bash scripts/deploy/prod/deploy-all.sh
```

## What lives where on the server

```
/opt/school-management/
├── app/                    rsynced from backend/
│   └── .venv/              created on first deploy
├── frontend/dist/          rsynced from frontend/dist/
├── logs/                   gunicorn access/error logs
├── backups/                app_<ts>.tgz + db_<ts>.sql.gz (auto-pruned >30d)
├── .env                    secrets (chmod 600 school:school)
├── .my.cnf                 mysqldump credentials (chmod 600 school:school)
└── .db_password            generated DB password (chmod 600 root, kept for re-provision)
```

## Slash commands

`.claude/commands/` mirrors uploadmytds:
`/provision-test`, `/deploy-test`, `/deploy-test-frontend`, `/deploy-test-all`,
`/deploy-prod`, `/deploy-prod-frontend`, `/deploy-prod-all`, `/clean-logs`.
