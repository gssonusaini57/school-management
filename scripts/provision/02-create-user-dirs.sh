#!/usr/bin/env bash
# Create the `school` system user and the /opt/school-management/* tree.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"
require_env SERVER SSH_KEY SSH_USER

log_step "02 · Create system user + directories"

ssh_run "bash -s" <<'REMOTE'
set -euo pipefail
APP_ROOT=/opt/school-management

if ! id school >/dev/null 2>&1; then
  useradd --system --home "$APP_ROOT" --shell /usr/sbin/nologin school
  echo "[server] Created user: school"
else
  echo "[server] User school already exists"
fi

mkdir -p "$APP_ROOT/app" "$APP_ROOT/frontend/dist" "$APP_ROOT/logs" "$APP_ROOT/backups"
chown -R school:school "$APP_ROOT"
# 755 on the root dir so nginx (www-data) can traverse it to serve frontend/dist/.
# Secret files inside are 600 (set by step 03/04), so they stay private regardless.
chmod 755 "$APP_ROOT"
echo "[server] Tree ready under $APP_ROOT (school:school 755 — secrets inside stay 600)"
REMOTE

log_ok "User + dirs OK"
