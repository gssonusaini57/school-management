#!/usr/bin/env bash
# Clone the PROD database into the TEST instance's database. Both live on the
# same server, so this is one SSH session and the data never leaves the box.
# Rerunnable. REPLACES every table in the test DB.
#
#   bash scripts/deploy/test/sync-from-prod.sh              # asks you to type the target DB name
#   ASSUME_YES=1 bash scripts/deploy/test/sync-from-prod.sh  # non-interactive (intent confirmed elsewhere)
#
# Pre-condition: the test instance is provisioned and deployed at least once
# (scripts/provision/provision.sh, then scripts/deploy/test/deploy-all.sh).
#
# What happens on the server (set -euo pipefail, stops at the first failure):
#   1. guards: distinct DBs, roots and MySQL users; the test .env points at the
#      test DB; the test credentials can NOT read the prod DB; test venv exists
#   2. dump PROD to $APP_ROOT/backups/db_prodclone_<ts>.sql.gz — a consistent
#      --single-transaction snapshot, no locks on live prod — and verify it completed
#      (the test DB is untouched until this succeeded)
#   3. back up the current TEST DB to db_presync_<ts>.sql.gz
#   4. stop the test service, DROP + CREATE the test DB (its own grant allows it),
#      import, verify the alembic revision matches prod, compare row counts
#   5. `alembic upgrade head` with the code deployed on TEST (no-op when TEST runs
#      prod's schema; otherwise a real migration rehearsal on prod-shaped data)
#   6. start the test service; then a health check from here
# PROD is only ever read. Email stays off on TEST (no SMTP keys in its .env), so
# the cloned staff addresses can't be mailed from a test run.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

[ "$ENV" = "test" ] || die "sync-from-prod.sh only ever targets ENV=test"

# Prod knobs, read in a subshell so prod's env can't leak into this one.
eval "$(bash -c 'source "$1" >/dev/null; printf "SRC_SERVER=%q SRC_ROOT=%q SRC_DB=%q\n" "$SERVER" "$APP_ROOT" "$DB_NAME"' _ "$HERE/../prod/env.sh")"

[ "$SRC_SERVER" = "$SERVER" ] || die "prod ($SRC_SERVER) and test ($SERVER) are on different servers — this script only clones within one box"
[ "$SRC_DB" != "$DB_NAME" ]   || die "source and target DB are both '$DB_NAME'"
[ "$SRC_ROOT" != "$APP_ROOT" ] || die "source and target APP_ROOT are both '$APP_ROOT'"
case "$DB_NAME" in *test*) ;; *) die "refusing: target DB '$DB_NAME' does not look like a test database";; esac

ssh_preflight
log_step "Clone PROD data → TEST on $SERVER"
log_info "Source: $SRC_DB  ($SRC_ROOT) — read-only snapshot"
log_warn "Target: $DB_NAME  ($APP_ROOT) — every table is DROPPED and replaced; $SERVICE_NAME stops during the import"
if [ "${ASSUME_YES:-0}" != "1" ]; then
  typed=""
  if { true </dev/tty; } 2>/dev/null; then
    read -r -p "Type the target DB name ($DB_NAME) to confirm: " typed </dev/tty || true
  else
    read -r -p "Type the target DB name ($DB_NAME) to confirm: " typed || true
  fi
  [ "$typed" = "$DB_NAME" ] || die "Aborted"
else
  log_warn "Confirmed via ASSUME_YES=1"
fi

TS=$(date +%Y%m%d_%H%M%S)
ssh_run "TS='$TS' SRC_ROOT='$SRC_ROOT' SRC_DB='$SRC_DB' DST_ROOT='$APP_ROOT' DST_DB='$DB_NAME' APP_USER='$APP_USER' SERVICE_NAME='$SERVICE_NAME' bash -s" <<'REMOTE'
set -euo pipefail
SRC_CNF="$SRC_ROOT/.my.cnf"
DST_CNF="$DST_ROOT/.my.cnf"
BK="$DST_ROOT/backups"
DUMP="$BK/db_prodclone_${TS}.sql.gz"
PRE="$BK/db_presync_${TS}.sql.gz"
# --no-tablespaces: the app users have no PROCESS privilege (MySQL 8 needs it for
# tablespace metadata). --hex-blob: student documents are LONGBLOBs.
DUMP_OPTS="--single-transaction --quick --no-tablespaces --hex-blob --set-gtid-purged=OFF --default-character-set=utf8mb4 --max-allowed-packet=512M"

say()  { echo "[server] $*"; }
fail() { echo "[server] ERROR: $*" >&2; exit 1; }
STOPPED=0
on_exit() {
  rc=$?
  if [ $rc -ne 0 ] && [ $STOPPED -eq 1 ]; then
    echo "[server] $SERVICE_NAME was left STOPPED. To put the previous test data back:" >&2
    [ -f "$PRE" ] && echo "[server]   mysql --defaults-file=$DST_CNF -e 'DROP DATABASE IF EXISTS \`$DST_DB\`; CREATE DATABASE \`$DST_DB\`' && zcat $PRE | mysql --defaults-file=$DST_CNF --max-allowed-packet=512M $DST_DB && systemctl start $SERVICE_NAME" >&2
  fi
}
trap on_exit EXIT

# ── 1. guards ────────────────────────────────────────────────────────────────
[ -f "$SRC_CNF" ] || fail "$SRC_CNF missing"
[ -f "$DST_CNF" ] || fail "$DST_CNF missing — provision the test instance first"
cnf_user() { sed -n 's/^[[:space:]]*user[[:space:]]*=[[:space:]]*//p' "$1" | head -1; }
SRC_USER=$(cnf_user "$SRC_CNF"); DST_USER=$(cnf_user "$DST_CNF")
[ -n "$DST_USER" ] && [ "$SRC_USER" != "$DST_USER" ] || fail "prod and test .my.cnf use the same MySQL user ('$DST_USER')"
grep -qE "^DATABASE_URL=.*/${DST_DB}\$" "$DST_ROOT/.env" || fail "$DST_ROOT/.env DATABASE_URL does not point at $DST_DB"
if mysql --defaults-file="$DST_CNF" -e "USE \`$SRC_DB\`" >/dev/null 2>&1; then
  fail "the test MySQL user can read $SRC_DB — refusing (its grants are wider than its own DB)"
fi
[ -x "$DST_ROOT/app/.venv/bin/alembic" ] || fail "no test venv at $DST_ROOT/app/.venv — run scripts/deploy/test/deploy-all.sh first"
SRC_REV=$(mysql --defaults-file="$SRC_CNF" -N -e "SELECT version_num FROM \`$SRC_DB\`.alembic_version")
say "prod schema revision: $SRC_REV"
mkdir -p "$BK"; chmod 700 "$BK"

# ── 2. dump prod to a file and verify it ────────────────────────────────────
mysqldump --defaults-file="$SRC_CNF" $DUMP_OPTS "$SRC_DB" | gzip > "$DUMP"
chmod 600 "$DUMP"
zcat "$DUMP" | tail -1 | grep -q "Dump completed" || fail "prod dump incomplete: $DUMP"
say "prod dump OK: $DUMP ($(du -h "$DUMP" | cut -f1))"

# ── 3. pre-sync backup of the current test DB ───────────────────────────────
TABLES=$(mysql --defaults-file="$DST_CNF" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DST_DB'")
if [ "${TABLES:-0}" -gt 0 ]; then
  mysqldump --defaults-file="$DST_CNF" $DUMP_OPTS "$DST_DB" | gzip > "$PRE"
  chmod 600 "$PRE"
  say "test pre-sync backup: $PRE ($TABLES tables)"
else
  PRE=""
  say "test DB is empty — no pre-sync backup needed"
fi

# ── 4. replace the test DB ──────────────────────────────────────────────────
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
STOPPED=1
mysql --defaults-file="$DST_CNF" -e "DROP DATABASE IF EXISTS \`$DST_DB\`; CREATE DATABASE \`$DST_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
zcat "$DUMP" | mysql --defaults-file="$DST_CNF" --max-allowed-packet=512M "$DST_DB"

DST_REV=$(mysql --defaults-file="$DST_CNF" -N -e "SELECT version_num FROM alembic_version" "$DST_DB")
[ "$DST_REV" = "$SRC_REV" ] || fail "revision mismatch after import: prod=$SRC_REV test=$DST_REV"
printf "[server] %-26s %8s %8s\n" "table" "prod" "test"
for t in students staff staff_classes student_documents attendance attendance_records marks marks_batches class_subjects subject_exam_components fee_payments notices; do
  s=$(mysql --defaults-file="$SRC_CNF" -N -e "SELECT COUNT(*) FROM \`$SRC_DB\`.\`$t\`" 2>/dev/null || echo "-")
  d=$(mysql --defaults-file="$DST_CNF" -N -e "SELECT COUNT(*) FROM \`$t\`" "$DST_DB" 2>/dev/null || echo "-")
  flag=""; [ "$s" = "$d" ] || flag="  (prod is live — changes after the snapshot are expected)"
  printf "[server] %-26s %8s %8s%s\n" "$t" "$s" "$d" "$flag"
done

# ── 5. migrate to the deployed test code's head ─────────────────────────────
cd "$DST_ROOT/app"
set -a; . "$DST_ROOT/.env"; set +a
.venv/bin/alembic upgrade head
say "test schema revision now: $(mysql --defaults-file="$DST_CNF" -N -e "SELECT version_num FROM alembic_version" "$DST_DB")"

# ── 6. restart ──────────────────────────────────────────────────────────────
chown "$APP_USER:$APP_USER" "$BK"/*.sql.gz 2>/dev/null || true
systemctl start "$SERVICE_NAME"
sleep 3
systemctl is-active "$SERVICE_NAME" >/dev/null || { journalctl -u "$SERVICE_NAME" -n 50 --no-pager; fail "$SERVICE_NAME did not start"; }
STOPPED=0
say "$SERVICE_NAME is active"
REMOTE

log_step "Health check"
health_wait "${BASE_URL}${HEALTH_PATH}" || die "TEST unhealthy after the sync — bash scripts/deploy/test/check-logs.sh 15m"
log_ok "TEST now holds a copy of PROD data · ${BASE_URL}${SITE_URL_PATH}"
