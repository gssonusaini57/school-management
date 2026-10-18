#!/usr/bin/env bash
# Pull a fresh mysqldump of the TEST instance DB ($DB_NAME, from env.sh).
# Output: ~/Downloads/db-backups/school_test_<timestamp>.sql.gz
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

ssh_preflight

TS=$(date +%Y%m%d_%H%M%S)
LOCAL_DIR="$HOME/Downloads/db-backups"
mkdir -p "$LOCAL_DIR"
LOCAL_FILE="$LOCAL_DIR/school_${ENV}_${TS}.sql.gz"

log_info "Dumping $DB_NAME on $SERVER…"
ssh_run "TS=$TS $(remote_env) bash -s" <<'REMOTE' >/dev/null
set -euo pipefail
[ -f "$APP_ROOT/.my.cnf" ] || { echo "[server] $APP_ROOT/.my.cnf missing — provisioning incomplete" >&2; exit 1; }
mkdir -p "$APP_ROOT/backups"
mysqldump --defaults-file="$APP_ROOT/.my.cnf" --single-transaction --quick --no-tablespaces "$DB_NAME" \
  | gzip > "$APP_ROOT/backups/db_manual_${TS}.sql.gz"
zcat "$APP_ROOT/backups/db_manual_${TS}.sql.gz" | tail -1 | grep -q "Dump completed" \
  || { echo "[server] dump incomplete" >&2; exit 1; }
chmod 600 "$APP_ROOT/backups/db_manual_${TS}.sql.gz"
echo "[server] $APP_ROOT/backups/db_manual_${TS}.sql.gz"
REMOTE

log_info "Downloading dump → $LOCAL_FILE"
scp_down "${SSH_USER}@${SERVER}:$APP_ROOT/backups/db_manual_${TS}.sql.gz" "$LOCAL_FILE"

log_ok "Local: $LOCAL_FILE  ($(du -h "$LOCAL_FILE" | awk '{print $1}'))"
