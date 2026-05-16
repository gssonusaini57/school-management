#!/usr/bin/env bash
# Shared deploy library. Source this from any test/prod deploy script.
# Caller must export: SERVER, SSH_USER, SSH_KEY, DOMAIN, ENV (test|prod)
set -euo pipefail

# ── Locate repo root from caller ───────────────────────────────────────────
LIB_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$LIB_HERE/../../.." && pwd)"

# ── Pull in provisioning's color logger + ssh wrappers ─────────────────────
# shellcheck disable=SC1091
source "$REPO_ROOT/scripts/provision/00-common.sh"

# ── Standard remote paths (mirror provisioning layout) ─────────────────────
APP_ROOT=/opt/school-management
APP_DIR=$APP_ROOT/app
FRONTEND_DIR=$APP_ROOT/frontend/dist
PUBLIC_SITE_DIR=$APP_ROOT/public-site/dist
LOGS_DIR=$APP_ROOT/logs
BACKUPS_DIR=$APP_ROOT/backups

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
  ssh_run_q "TS=$ts bash -s" <<'REMOTE' >/dev/null
set -e
APP_ROOT=/opt/school-management
mkdir -p "$APP_ROOT/backups"
if [ -d "$APP_ROOT/app" ] && [ "$(ls -A "$APP_ROOT/app" 2>/dev/null)" ]; then
  tar czf "$APP_ROOT/backups/app_${TS}.tgz" -C "$APP_ROOT/app" . 2>/dev/null || true
fi
if [ -f "$APP_ROOT/.my.cnf" ]; then
  mysqldump --defaults-file="$APP_ROOT/.my.cnf" --single-transaction school_management 2>/dev/null \
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
  log_warn "Rolling back app to snapshot $ts"
  ssh_run "TS=$ts bash -s" <<'REMOTE'
set -e
APP_ROOT=/opt/school-management
SNAP="$APP_ROOT/backups/app_${TS}.tgz"
if [ ! -f "$SNAP" ]; then
  echo "[server] Snapshot $SNAP missing — cannot rollback" >&2
  exit 1
fi
systemctl stop school-management 2>/dev/null || true
rm -rf "$APP_ROOT/app"/*
tar xzf "$SNAP" -C "$APP_ROOT/app"
chown -R school:school "$APP_ROOT"
systemctl start school-management
echo "[server] Rolled back to $TS"
REMOTE
}

# ── Sanity-parse all backend Python (catches syntax errors before SSH) ─────
local_python_lint() {
  log_info "Sanity-parsing backend Python…"
  python3 - <<EOF
import ast, sys, pathlib
errs = 0
for p in pathlib.Path("$REPO_ROOT/backend").rglob("*.py"):
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
  log_info "Building frontend (Vite)…"
  ( cd "$REPO_ROOT/frontend" && npm ci --silent --no-audit --no-fund && npm run build )
  [ -f "$REPO_ROOT/frontend/dist/index.html" ] || die "Vite build missing dist/index.html"
  log_ok "Frontend built ($(du -sh "$REPO_ROOT/frontend/dist" | awk '{print $1}'))"
}

# ── Push backend source ────────────────────────────────────────────────────
push_backend() {
  log_info "Sync backend → ${SERVER}:${APP_DIR}"
  scp_up --delete \
    --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
    --exclude '.pytest_cache' --exclude 'tests' \
    "$REPO_ROOT/backend/" "${SSH_USER}@${SERVER}:${APP_DIR}/"
}

push_frontend() {
  log_info "Sync frontend dist → ${SERVER}:${FRONTEND_DIR}"
  ssh_run "mkdir -p $FRONTEND_DIR"
  scp_up --delete "$REPO_ROOT/frontend/dist/" "${SSH_USER}@${SERVER}:${FRONTEND_DIR}/"
}

# ── Remote: install/upgrade venv + alembic + restart ───────────────────────
remote_install_and_restart() {
  log_info "Remote: pip install + alembic upgrade + restart"
  ssh_run "bash -s" <<'REMOTE'
set -euo pipefail
APP_ROOT=/opt/school-management
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

chown -R school:school "$APP_ROOT"
systemctl daemon-reload || true
systemctl restart school-management
systemctl is-active school-management >/dev/null || { journalctl -u school-management -n 50 --no-pager; exit 1; }
echo "[server] school-management is active"
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
  local HEALTH_URL="https://${DOMAIN}/school/api/health"
  if ! health_wait "$HEALTH_URL"; then
    log_err "Health check failed — rolling back"
    remote_rollback "$SNAP_TS"
    return 1
  fi

  log_ok "Deployed at $(date '+%Y-%m-%d %H:%M:%S') · URL: https://${DOMAIN}/school/"
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
  local HEALTH_URL="https://${DOMAIN}/school/api/health"
  if ! health_wait "$HEALTH_URL"; then
    log_err "Health check failed — rolling back"
    remote_rollback "$SNAP_TS"
    return 1
  fi
  log_ok "Backend deployed · URL: https://${DOMAIN}/school/api/health"
}

deploy_frontend_only() {
  ssh_preflight
  local_frontend_build

  log_step "Push frontend dist"
  push_frontend

  ssh_run "chown -R school:school /opt/school-management/frontend"
  log_ok "Frontend deployed · URL: https://${DOMAIN}/school/"
}

# ── Public marketing site (Eleventy + Tailwind CLI) ────────────────────────
local_public_site_build() {
  log_info "Building public-site (Eleventy + Tailwind)…"
  ( cd "$REPO_ROOT/public-site" && npm ci --silent --no-audit --no-fund && npm run build )
  [ -f "$REPO_ROOT/public-site/dist/index.html" ] || die "Public-site build missing dist/index.html"
  [ -f "$REPO_ROOT/public-site/dist/en/index.html" ] || die "Public-site build missing dist/en/index.html"
  [ -f "$REPO_ROOT/public-site/dist/pa/index.html" ] || die "Public-site build missing dist/pa/index.html"
  log_ok "Public-site built ($(du -sh "$REPO_ROOT/public-site/dist" | awk '{print $1}'))"
}

push_public_site() {
  log_info "Sync public-site dist → ${SERVER}:${PUBLIC_SITE_DIR}"
  ssh_run "mkdir -p $PUBLIC_SITE_DIR"
  scp_up --delete "$REPO_ROOT/public-site/dist/" "${SSH_USER}@${SERVER}:${PUBLIC_SITE_DIR}/"
}

deploy_public_site_only() {
  ssh_preflight
  local_public_site_build

  log_step "Push public-site dist"
  push_public_site

  ssh_run "chown -R school:school /opt/school-management/public-site"
  log_ok "Public site deployed → ${PUBLIC_SITE_DIR}"
  log_info "Manual nginx step required if first deploy — see deploy/nginx.public-site.conf"
}
