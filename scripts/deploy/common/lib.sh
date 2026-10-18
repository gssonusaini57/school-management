#!/usr/bin/env bash
# Shared deploy library. Source this from any test/prod deploy script AFTER that
# environment's env.sh.
#
# Caller must export (all come from scripts/deploy/<env>/env.sh):
#   SERVER SSH_USER SSH_KEY DOMAIN BASE_URL ENV
#   URL layout:     URL_PREFIX VITE_BASE VITE_API_URL HEALTH_PATH SITE_URL_PATH SITE_BASE_PATH PUBLIC_SITE
#   instance knobs: APP_ROOT APP_USER SERVICE_NAME APP_PORT DB_NAME DB_USER
#
# Optional: SRC_ROOT — tree whose backend/ + frontend/ get built and shipped
# (default: this checkout). Point it at a clean export to deploy committed code
# while the working tree holds unfinished work:
#   SRC_ROOT=$(mktemp -d) && git archive HEAD backend frontend packages | tar -x -C "$SRC_ROOT"
#
# PROD and TEST are two instances on ONE box, so nothing in here may hardcode
# /opt/school-management, the `school` user, the `school-management` unit, port
# 8000 or the `school_management` database — each is a knob with the PROD value
# as its default.
set -euo pipefail

# ── Locate repo root from caller ───────────────────────────────────────────
LIB_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$LIB_HERE/../../.." && pwd)"

# ── Pull in provisioning's color logger + ssh wrappers ─────────────────────
# shellcheck disable=SC1091
source "$REPO_ROOT/scripts/provision/00-common.sh"

# ── Instance knobs (defaults = the original single-instance PROD layout) ───
APP_ROOT="${APP_ROOT:-/opt/school-management}"
APP_USER="${APP_USER:-school}"
SERVICE_NAME="${SERVICE_NAME:-school-management}"
DB_NAME="${DB_NAME:-school_management}"
URL_PREFIX="${URL_PREFIX-}"
BASE_URL="${BASE_URL:-https://${DOMAIN:?set DOMAIN or BASE_URL}}"
HEALTH_PATH="${HEALTH_PATH:-${URL_PREFIX}/api/health}"
SITE_URL_PATH="${SITE_URL_PATH:-${URL_PREFIX}/admin/}"
PUBLIC_SITE="${PUBLIC_SITE:-1}"
APK_LOCAL_NAME="${APK_LOCAL_NAME:-kis-attendance.apk}"
MANIFEST_NAME="${MANIFEST_NAME:-app-version.json}"
DOWNLOADS_URL="${DOWNLOADS_URL:-${BASE_URL}${URL_PREFIX}/downloads}"
APP_DIR=$APP_ROOT/app
FRONTEND_DIR=$APP_ROOT/frontend/dist
PUBLIC_SITE_DIR=$APP_ROOT/public-site/dist
SRC_ROOT="${SRC_ROOT:-$REPO_ROOT}"
[ -d "$SRC_ROOT/backend" ] || die "SRC_ROOT=$SRC_ROOT has no backend/"
validate_layout
if [ "$SRC_ROOT" != "$REPO_ROOT" ]; then
  log_warn "Shipping sources from SRC_ROOT=$SRC_ROOT (not this working tree)"
fi

# Remote scripts below are quoted heredocs (<<'REMOTE'), so local variables are
# NOT expanded inside them. Whatever the server side needs travels as env
# assignments in front of `bash -s` — this prints that prefix.
remote_env() {
  printf "APP_ROOT='%s' APP_USER='%s' SERVICE_NAME='%s' DB_NAME='%s'" \
    "$APP_ROOT" "$APP_USER" "$SERVICE_NAME" "$DB_NAME"
}

# ── Health check loop (8 attempts × 5s) ────────────────────────────────────
health_wait() {
  local url=$1
  local n=${2:-8}
  local i
  for ((i=1; i<=n; i++)); do
    if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
      log_ok "Healthy: $url"
      return 0
    fi
    sleep 5
  done
  log_err "Health check failed after $n attempts: $url"
  return 1
}

# ── Pre-deploy snapshot (returns timestamp on stdout) ──────────────────────
remote_snapshot() {
  local ts; ts=$(date +%Y%m%d_%H%M%S)
  ssh_run_q "TS=$ts $(remote_env) bash -s" <<'REMOTE' >/dev/null
set -e
mkdir -p "$APP_ROOT/backups"
if [ -d "$APP_ROOT/app" ] && [ "$(ls -A "$APP_ROOT/app" 2>/dev/null)" ]; then
  tar czf "$APP_ROOT/backups/app_${TS}.tgz" -C "$APP_ROOT/app" . 2>/dev/null || true
fi
if [ -f "$APP_ROOT/.my.cnf" ]; then
  # --no-tablespaces: the app's DB user has no PROCESS privilege, which MySQL 8
  # demands for tablespace metadata; without the flag mysqldump errors out.
  mysqldump --defaults-file="$APP_ROOT/.my.cnf" --single-transaction --no-tablespaces "$DB_NAME" 2>/dev/null \
    | gzip > "$APP_ROOT/backups/db_${TS}.sql.gz" 2>/dev/null || true
fi
# Prune backups older than 30 days
find "$APP_ROOT/backups" -name 'app_*.tgz' -mtime +30 -delete 2>/dev/null || true
find "$APP_ROOT/backups" -name 'db_*.sql.gz' -mtime +30 -delete 2>/dev/null || true
REMOTE
  echo "$ts"
}

# ── Roll back to a snapshot ─────────────────────────────────────────────────
remote_rollback() {
  local ts=$1
  log_warn "Rolling back $SERVICE_NAME to snapshot $ts"
  ssh_run "TS=$ts $(remote_env) bash -s" <<'REMOTE'
set -e
: "${APP_ROOT:?}" "${SERVICE_NAME:?}" "${APP_USER:?}"
SNAP="$APP_ROOT/backups/app_${TS}.tgz"
if [ ! -f "$SNAP" ]; then
  echo "[server] Snapshot $SNAP missing — cannot rollback" >&2
  exit 1
fi
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
rm -rf "$APP_ROOT/app"/*
tar xzf "$SNAP" -C "$APP_ROOT/app"
chown -R "$APP_USER:$APP_USER" "$APP_ROOT"
systemctl start "$SERVICE_NAME"
echo "[server] Rolled back $SERVICE_NAME to $TS"
REMOTE
}

# ── Sanity-parse all backend Python (catches syntax errors before SSH) ─────
local_python_lint() {
  log_info "Sanity-parsing backend Python…"
  python3 - <<EOF
import ast, sys, pathlib
errs = 0
for p in pathlib.Path("$SRC_ROOT/backend").rglob("*.py"):
    try:
        ast.parse(p.read_text())
    except SyntaxError as e:
        print(f"SYNTAX {p}: {e}"); errs += 1
sys.exit(errs)
EOF
  log_ok "Backend Python parses clean"
}

# ── Build frontend locally ─────────────────────────────────────────────────
local_frontend_build() {
  require_env VITE_BASE VITE_API_URL
  log_info "Building frontend (Vite, base=${VITE_BASE}, api=${VITE_API_URL})…"
  ( cd "$SRC_ROOT/frontend" && npm ci --silent --no-audit --no-fund \
      && VITE_BASE="$VITE_BASE" VITE_API_URL="$VITE_API_URL" npm run build )
  [ -f "$SRC_ROOT/frontend/dist/index.html" ] || die "Vite build missing dist/index.html"
  log_ok "Frontend built ($(du -sh "$SRC_ROOT/frontend/dist" | awk '{print $1}'))"
}

# ── Push backend source ────────────────────────────────────────────────────
push_backend() {
  log_info "Sync backend → ${SERVER}:${APP_DIR}"
  scp_up --delete \
    --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
    --exclude '.pytest_cache' --exclude 'tests' \
    "$SRC_ROOT/backend/" "${SSH_USER}@${SERVER}:${APP_DIR}/"
}

push_frontend() {
  log_info "Sync frontend dist → ${SERVER}:${FRONTEND_DIR}"
  ssh_run "mkdir -p $FRONTEND_DIR" </dev/null
  # downloads/ is excluded (so --delete never touches it) and published by
  # push_downloads instead — see there.
  scp_up --delete --exclude 'downloads/' "$SRC_ROOT/frontend/dist/" "${SSH_USER}@${SERVER}:${FRONTEND_DIR}/"
  push_downloads
}

# ── Publish this environment's Android APK + force-update manifest ─────────
# frontend/public/downloads/ holds BOTH flavours' gitignored build outputs
# (scripts/build-android.sh), and Vite copies everything in public/ into dist/.
# Shipping dist/downloads/ as-is would publish the PROD-flavour APK on TEST, and
# rsync --delete would wipe the server's APK whenever the local one is missing.
# So frontend syncs exclude downloads/ and this step publishes exactly this env's
# pair under the stable names — and never deletes anything. Artifacts are read
# from this checkout even when SRC_ROOT is a clean export (exports carry none).
push_downloads() {
  local art="$REPO_ROOT/frontend/public/downloads" dst="$FRONTEND_DIR/downloads"
  if [ ! -f "$art/$APK_LOCAL_NAME" ]; then
    log_warn "No local $APK_LOCAL_NAME — the server's downloads/ is left as-is (build: scripts/build-android.sh; publish: upload-apk.sh)"
    return 0
  fi
  ssh_run "mkdir -p '$dst'" </dev/null
  scp_up "$art/$APK_LOCAL_NAME" "${SSH_USER}@${SERVER}:${dst}/kis-attendance.apk"
  if [ -f "$art/$MANIFEST_NAME" ]; then
    scp_up "$art/$MANIFEST_NAME" "${SSH_USER}@${SERVER}:${dst}/${MANIFEST_NAME}"
  fi
  log_ok "Published $APK_LOCAL_NAME → ${DOWNLOADS_URL}/kis-attendance.apk (+ $MANIFEST_NAME)"
}

# ── Remote: install/upgrade venv + alembic + restart ───────────────────────
remote_install_and_restart() {
  log_info "Remote: pip install + alembic upgrade + restart $SERVICE_NAME"
  ssh_run "$(remote_env) bash -s" <<'REMOTE'
set -euo pipefail
cd "$APP_ROOT/app"

if [ ! -d .venv ]; then
  python3.12 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet --no-input -r requirements.txt

# Load env vars (DATABASE_URL etc.) for alembic
set -a
. "$APP_ROOT/.env"
set +a
.venv/bin/alembic upgrade head

chown -R "$APP_USER:$APP_USER" "$APP_ROOT"
systemctl daemon-reload || true
systemctl restart "$SERVICE_NAME"
systemctl is-active "$SERVICE_NAME" >/dev/null || { journalctl -u "$SERVICE_NAME" -n 50 --no-pager; exit 1; }
echo "[server] $SERVICE_NAME is active"
REMOTE
}

# ── Single-command full deploy used by deploy-all.sh ───────────────────────
deploy_full() {
  ssh_preflight
  local_python_lint
  local_frontend_build

  log_step "Pre-deploy snapshot"
  local SNAP_TS
  SNAP_TS=$(remote_snapshot)
  log_ok "Snapshot: $SNAP_TS"

  log_step "Push code"
  push_backend
  push_frontend

  log_step "Install + restart"
  if ! remote_install_and_restart; then
    log_err "Remote install/restart failed — rolling back"
    remote_rollback "$SNAP_TS"
    return 1
  fi

  log_step "Health check"
  local HEALTH_URL="${BASE_URL}${HEALTH_PATH}"
  if ! health_wait "$HEALTH_URL"; then
    log_err "Health check failed — rolling back"
    remote_rollback "$SNAP_TS"
    return 1
  fi

  log_ok "Deployed at $(date '+%Y-%m-%d %H:%M:%S') · URL: ${BASE_URL}${SITE_URL_PATH}"
  log_info "Snapshot retained: app_${SNAP_TS}.tgz · db_${SNAP_TS}.sql.gz"
}

deploy_backend_only() {
  ssh_preflight
  local_python_lint

  log_step "Pre-deploy snapshot"
  local SNAP_TS; SNAP_TS=$(remote_snapshot)
  log_ok "Snapshot: $SNAP_TS"

  log_step "Push backend"
  push_backend

  log_step "Install + restart"
  if ! remote_install_and_restart; then
    log_err "Backend deploy failed — rolling back"
    remote_rollback "$SNAP_TS"
    return 1
  fi

  log_step "Health check"
  local HEALTH_URL="${BASE_URL}${HEALTH_PATH}"
  if ! health_wait "$HEALTH_URL"; then
    log_err "Health check failed — rolling back"
    remote_rollback "$SNAP_TS"
    return 1
  fi
  log_ok "Backend deployed · URL: ${HEALTH_URL}"
}

deploy_frontend_only() {
  ssh_preflight
  local_frontend_build

  log_step "Push frontend dist"
  push_frontend

  ssh_run "chown -R '$APP_USER:$APP_USER' '$APP_ROOT/frontend'"
  log_ok "Frontend deployed · URL: ${BASE_URL}${SITE_URL_PATH}"
}

# ── Public marketing site (Eleventy + Tailwind CLI) — PROD only ───────────
require_public_site() {
  [ "$PUBLIC_SITE" = "1" ] || die "ENV=${ENV:-?} has no public marketing site (PUBLIC_SITE=0 in its env.sh)"
}

local_public_site_build() {
  require_public_site
  log_info "Building public-site (Eleventy + Tailwind, basePath='${SITE_BASE_PATH-}')…"
  # Note: `-` (not `:-`) so an explicit empty SITE_BASE_PATH (apex root) is honoured.
  ( cd "$SRC_ROOT/public-site" && npm ci --silent --no-audit --no-fund \
      && SITE_BASE_PATH="${SITE_BASE_PATH-}" npm run build )
  [ -f "$SRC_ROOT/public-site/dist/index.html" ] || die "Public-site build missing dist/index.html"
  [ -f "$SRC_ROOT/public-site/dist/en/index.html" ] || die "Public-site build missing dist/en/index.html"
  [ -f "$SRC_ROOT/public-site/dist/pa/index.html" ] || die "Public-site build missing dist/pa/index.html"
  log_ok "Public-site built ($(du -sh "$SRC_ROOT/public-site/dist" | awk '{print $1}'))"
}

push_public_site() {
  require_public_site
  log_info "Sync public-site dist → ${SERVER}:${PUBLIC_SITE_DIR}"
  ssh_run "mkdir -p $PUBLIC_SITE_DIR" </dev/null
  scp_up --delete "$SRC_ROOT/public-site/dist/" "${SSH_USER}@${SERVER}:${PUBLIC_SITE_DIR}/"
}

deploy_public_site_only() {
  require_public_site
  ssh_preflight
  local_public_site_build

  log_step "Push public-site dist"
  push_public_site

  ssh_run "chown -R '$APP_USER:$APP_USER' '$APP_ROOT/public-site'"
  log_ok "Public site deployed → ${PUBLIC_SITE_DIR}"
  log_info "First deploy only: the vhost (deploy/nginx.kisschool.conf) must already serve ${PUBLIC_SITE_DIR}"
}
