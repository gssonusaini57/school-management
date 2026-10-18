#!/usr/bin/env bash
# Create the instance's system user ($APP_USER) and the $APP_ROOT/* tree.
# Idempotent. PROD and TEST each have their own user + tree on the same box.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"
require_env SERVER SSH_KEY SSH_USER APP_ROOT APP_USER

log_step "02 · Create system user + directories ($APP_USER @ $APP_ROOT)"

ssh_run "APP_ROOT='$APP_ROOT' APP_USER='$APP_USER' bash -s" <<'REMOTE'
set -euo pipefail

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_ROOT" --shell /usr/sbin/nologin "$APP_USER"
  echo "[server] Created user: $APP_USER"
else
  echo "[server] User $APP_USER already exists"
fi

mkdir -p "$APP_ROOT/app" "$APP_ROOT/frontend/dist" "$APP_ROOT/logs" "$APP_ROOT/backups"
chown -R "$APP_USER:$APP_USER" "$APP_ROOT"
# 755 on the root dir so nginx (www-data) can traverse it to serve frontend/dist/.
# Secret files inside are 600 (set by step 03/04), so they stay private regardless.
chmod 755 "$APP_ROOT"
# DB dumps land in backups/ — keep them away from other local users.
chmod 700 "$APP_ROOT/backups"
echo "[server] Tree ready under $APP_ROOT ($APP_USER:$APP_USER 755; backups/ 700; secrets inside stay 600)"
REMOTE

log_ok "User + dirs OK"
