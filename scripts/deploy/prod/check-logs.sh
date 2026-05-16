#!/usr/bin/env bash
# Read-only log analysis on PROD. Mirrors test/check-logs.sh — same sections,
# different server. See that file for full docs.
#
# Usage:
#   bash scripts/deploy/prod/check-logs.sh           # default: --since 1h
#   bash scripts/deploy/prod/check-logs.sh 30m
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

SINCE_RAW="${1:-1 hour ago}"
case "$SINCE_RAW" in
  *m) SINCE="${SINCE_RAW%m} minutes ago" ;;
  *h) SINCE="${SINCE_RAW%h} hours ago" ;;
  *d) SINCE="${SINCE_RAW%d} days ago" ;;
  *) SINCE="$SINCE_RAW" ;;
esac

ssh_preflight

log_step "Log analysis · since '$SINCE' · ${SERVER} (PROD)"

ssh_run "SINCE=\"$SINCE\" bash -s" <<'REMOTE'
set -u
APP_ROOT=/opt/school-management
ERR=$APP_ROOT/logs/error.log
ACC=$APP_ROOT/logs/access.log

section() { printf '\n\033[36m── %s ─────────────────────────────────────\033[0m\n' "$1"; }

section "1. Service status"
systemctl is-active school-management || true
systemctl show school-management --no-page \
  --property=ActiveEnterTimestamp,MainPID,NRestarts,MemoryCurrent,Restart \
  | sed 's/^/  /'

section "2. journalctl --since '$SINCE'"
JLINES=$(journalctl -u school-management --since "$SINCE" --no-pager \
  | grep -E 'systemd\[1\]|ERROR|CRITICAL|WARN|Traceback|Exception' \
  | tail -40)
if [ -n "$JLINES" ]; then
  printf '%s\n' "$JLINES" | sed 's/^/  /'
else
  echo "  (no matching journal lines in window)"
fi

section "3. error.log tail (40 lines)"
if [ -f "$ERR" ]; then
  tail -40 "$ERR" | sed 's/^/  /'
else
  echo "  (no error.log at $ERR)"
fi

section "4. Recent Python tracebacks (last 3, with 15 lines of context)"
if [ -f "$ERR" ]; then
  awk '
    /Traceback \(most recent call last\):/ { in_tb=1; lines=0; print "  ---"; }
    in_tb {
      print "  " $0; lines++;
      if (lines >= 15) { in_tb=0; }
    }
  ' "$ERR" | tail -75
  if ! grep -q 'Traceback' "$ERR"; then
    echo "  (no tracebacks)"
  fi
else
  echo "  (no error.log)"
fi

section "5. access.log tail (20 lines)"
if [ -f "$ACC" ]; then
  tail -20 "$ACC" | sed 's/^/  /'
else
  echo "  (no access.log at $ACC)"
fi

section "6. Recent HTTP errors (4xx / 5xx, last 20)"
if [ -f "$ACC" ]; then
  grep -E ' (4[0-9][0-9]|5[0-9][0-9])$' "$ACC" 2>/dev/null \
    | tail -20 \
    | sed 's/^/  /' \
    || echo "  (none)"
  COUNT=$(grep -cE ' (4[0-9][0-9]|5[0-9][0-9])$' "$ACC" 2>/dev/null || echo 0)
  echo "  total in file: $COUNT"
else
  echo "  (no access.log)"
fi

section "Done"
REMOTE
