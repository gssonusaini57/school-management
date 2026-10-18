#!/usr/bin/env bash
# Render deploy/school-management.service for this instance and install it as
# /etc/systemd/system/$SERVICE_NAME.service. daemon-reload + enable (don't start —
# first start happens after the first deploy, when code + venv exist).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"
require_env SERVER SSH_KEY SSH_USER APP_ROOT APP_USER APP_PORT SERVICE_NAME

log_step "05 · Install systemd unit ($SERVICE_NAME.service, gunicorn :$APP_PORT)"

TEMPLATE="$ROOT/deploy/school-management.service"
[ -f "$TEMPLATE" ] || die "deploy/school-management.service missing"

RENDERED="$(mktemp)"
trap 'rm -f "$RENDERED"' EXIT
render_template "$TEMPLATE" "$RENDERED"

scp_up "$RENDERED" "${SSH_USER}@${SERVER}:/tmp/${SERVICE_NAME}.service"

ssh_run "SERVICE_NAME='$SERVICE_NAME' bash -s" <<'REMOTE'
set -euo pipefail
UNIT="/etc/systemd/system/${SERVICE_NAME}.service"
mv "/tmp/${SERVICE_NAME}.service" "$UNIT"
chown root:root "$UNIT"
chmod 644 "$UNIT"
systemctl daemon-reload
if ! systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
  systemctl enable "$SERVICE_NAME"
  echo "[server] Enabled ${SERVICE_NAME}.service"
else
  echo "[server] ${SERVICE_NAME}.service already enabled"
fi
echo "[server] (Not starting — first start runs after first deploy installs the venv)"
REMOTE

log_ok "systemd unit installed (enabled, not yet started)"
