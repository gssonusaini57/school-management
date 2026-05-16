#!/usr/bin/env bash
# Manual rollback to a chosen snapshot.
#   bash scripts/deploy/test/rollback.sh                  # lists snapshots
#   bash scripts/deploy/test/rollback.sh 20260507_123456  # restores given snapshot
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

ssh_preflight

if [ $# -eq 0 ]; then
  log_step "Available snapshots on $SERVER"
  ssh_run "ls -lh /opt/school-management/backups/ 2>/dev/null | tail -20" || true
  echo
  log_info "Run again with a timestamp, e.g.: bash $0 20260507_123456"
  exit 0
fi

TS="$1"
log_warn "About to roll back app to snapshot $TS on $SERVER"
confirm "This will stop school-management, replace /opt/school-management/app/, and restart. Continue?"
remote_rollback "$TS"

log_step "Health check after rollback"
HEALTH_URL="https://${DOMAIN}/school/api/health"
health_wait "$HEALTH_URL" || die "Service still unhealthy after rollback"

log_ok "Rolled back to $TS and service is healthy"
