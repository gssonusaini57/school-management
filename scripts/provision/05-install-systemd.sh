#!/usr/bin/env bash
# Install/refresh /etc/systemd/system/school-management.service from
# deploy/school-management.service. daemon-reload + enable (don't start —
# first start happens after first deploy when code+venv exist).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"
require_env SERVER SSH_KEY SSH_USER

log_step "05 · Install systemd unit"

[ -f "$ROOT/deploy/school-management.service" ] || die "deploy/school-management.service missing"

scp_up "$ROOT/deploy/school-management.service" "${SSH_USER}@${SERVER}:/tmp/school-management.service"

ssh_run "bash -s" <<'REMOTE'
set -euo pipefail
mv /tmp/school-management.service /etc/systemd/system/school-management.service
chown root:root /etc/systemd/system/school-management.service
chmod 644 /etc/systemd/system/school-management.service
systemctl daemon-reload
if ! systemctl is-enabled school-management >/dev/null 2>&1; then
  systemctl enable school-management
  echo "[server] Enabled school-management.service"
else
  echo "[server] school-management.service already enabled"
fi
echo "[server] (Not starting — first start runs after first deploy installs the venv)"
REMOTE

log_ok "systemd unit installed (enabled, not yet started)"
