# Deployment scripts

One-page cheatsheet. Both environments live on **one server, 69.62.72.137**
(SSH key `~/.ssh/enamfoss_prod`), next to the unrelated enamfoss Tomcat app:

| | PROD | TEST |
|---|---|---|
| URL | https://kisschool.in/ (`/admin/`, `/api/`, `/downloads/`, public site at `/`) | http://69.62.72.137/kisschool/admin/ (`/kisschool/api/`, `/kisschool/downloads/`; no public site; plain HTTP) |
| install dir · Linux user | `/opt/school-management` · `school` | `/opt/school-management-test` · `school-test` |
| systemd unit · gunicorn | `school-management` · 127.0.0.1:8000 | `school-management-test` · 127.0.0.1:8001 |
| MySQL DB · user | `school_management` · `school` | `school_management_test` · `school_test` |
| nginx | standalone vhost `deploy/nginx.kisschool.conf` → `/etc/nginx/conf.d/kisschool.conf` (installed by hand) | snippet from `deploy/nginx.school-test.conf` → `/etc/nginx/snippets/school-management-test.conf`, `include`d (one line) from the enamfoss bare-IP vhost |
| email | Zoho SMTP | off (no SMTP keys; the DB is a prod clone) |

**Every one of those values is a knob in `scripts/deploy/<env>/env.sh`.** `common/lib.sh`,
the provision steps and the `deploy/` templates only consume knobs — never hardcode
`/opt/school-management`, `school-management`, `8000` or `school_management` anywhere.

## Layout

```
scripts/
├── provision/              one-time per-instance setup (idempotent; reads deploy/$ENV/env.sh)
│   ├── 00-common.sh                 logging, ssh/rsync wrappers, confirm (ASSUME_YES), read_secret, render_template, validate_layout
│   ├── 01-install-prereqs.sh        python3.12, venv, mysql client libs, WeasyPrint libs + fonts
│   ├── 02-create-user-dirs.sh       $APP_USER + $APP_ROOT/{app,frontend/dist,logs,backups(700)}
│   ├── 03-create-mysql-db.sh        $DB_NAME + $DB_USER (refuses to ALTER a user another instance owns); admin via MYSQL_ROOT_PASSWORD or /etc/mysql/debian.cnf
│   ├── 04-write-env.sh              $APP_ROOT/.env (JWT secret generated on the server; APP_BASE_URL; SMTP only for prod; FORCE on prod refused)
│   ├── 05-install-systemd.sh        renders deploy/school-management.service → /etc/systemd/system/$SERVICE_NAME.service
│   ├── 06-install-nginx-snippet.sh  renders deploy/nginx.school-test.conf → $NGINX_SNIPPET + one include in the `server_name $DOMAIN` block (no-op when NGINX_SNIPPET is empty, i.e. prod)
│   └── provision.sh                 wrapper: inspect + confirm + run 01..06   (ENV=test default; ENV=prod for prod)
├── deploy/
│   ├── common/lib.sh                shared: snapshot / rollback / build / push / downloads / deploy_full …
│   ├── test/                        env.sh · deploy-{all,backend,frontend}.sh · sync-from-prod.sh · upload-apk.sh
│   │                                check-logs.sh · download-logs.sh · backup-db.sh · rollback.sh
│   └── prod/                        same set (+ deploy-public-site.sh, no sync); every deploy asks you to type DEPLOY PROD
├── build-android.sh                 signed APK per flavour (prod | test) + force-update manifest (URL from env.sh)
└── README.md (this file)
```

## Quick start (TEST)

```bash
bash scripts/provision/provision.sh --inspect-only   # read-only
bash scripts/provision/provision.sh                  # one-time (ASSUME_YES=1 for non-interactive)
bash scripts/deploy/test/deploy-all.sh               # ships the working tree
bash scripts/deploy/test/sync-from-prod.sh           # replace TEST data with a fresh prod clone
bash scripts/deploy/test/check-logs.sh 30m           # read-only log triage
bash scripts/deploy/test/rollback.sh [<timestamp>]   # list / restore code snapshots
```

Ship only **committed** code while the working tree holds unfinished work (the frontend
imports `packages/design-system`, so `packages` must be in the export):

```bash
SRC_ROOT=$(mktemp -d) && git archive HEAD backend frontend packages | tar -x -C "$SRC_ROOT"
SRC_ROOT="$SRC_ROOT" bash scripts/deploy/test/deploy-all.sh
```

## Android APKs

`bash scripts/build-android.sh test` → `frontend/public/downloads/kis-attendance-test.apk` +
`app-version-test.json`; `bash scripts/deploy/test/upload-apk.sh` publishes them as
`/kisschool/downloads/kis-attendance.apk` (verifies HTTP 200 + byte size before arming the
force-update manifest). Frontend deploys also publish **only their own env's** APK and never
delete a server's APK (downloads/ is excluded from the `rsync --delete`).

## Environment overrides

Connection values can be overridden at the call site:
`SCHOOL_TEST_SERVER`, `SCHOOL_TEST_SSH_USER`, `SCHOOL_TEST_SSH_KEY`, `SCHOOL_TEST_DOMAIN`,
`SCHOOL_TEST_BASE_URL` (and the `SCHOOL_PROD_*` equivalents). Instance knobs are fixed in env.sh.

## What lives where on the server (per instance)

```
$APP_ROOT/                  (755, $APP_USER)
├── app/                    rsynced from backend/  (+ .venv/ created on first deploy)
├── frontend/dist/          rsynced from frontend/dist/ (downloads/ managed separately)
├── logs/                   gunicorn access/error logs
├── backups/ (700)          app_<ts>.tgz + db_<ts>.sql.gz (pruned >30d); TEST also db_prodclone_* / db_presync_*
├── .env                    secrets (600, $APP_USER)
├── .my.cnf                 mysqldump credentials (600, $APP_USER)
└── .db_password            generated DB password (600, root)
```

## Slash commands

`.claude/commands/`: `/provision-test`, `/deploy-test`, `/deploy-test-frontend`, `/deploy-test-all`,
`/sync-test-data`, `/deploy-prod`, `/deploy-prod-frontend`, `/deploy-prod-all`,
`/deploy-prod-public-site`, `/release-android`, `/check-logs`, `/clean-logs`.
