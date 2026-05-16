#!/usr/bin/env bash
# Download recent app logs from PROD.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

ssh_preflight

TS=$(date +%Y%m%d_%H%M%S)
DEST="$REPO_ROOT/logs_backup_prod_${TS}"
mkdir -p "$DEST"

log_info "Downloading /opt/school-management/logs → $DEST"
scp_down "${SSH_USER}@${SERVER}:/opt/school-management/logs/" "$DEST/" || true

log_info "Capturing journalctl -u school-management --since '24 hours ago'"
ssh_run "journalctl -u school-management --since '24 hours ago' --no-pager" \
  > "$DEST/journalctl-school-management.log" 2>&1 || true

log_ok "Saved $(find "$DEST" -type f | wc -l | awk '{print $1}') file(s) to $DEST"
