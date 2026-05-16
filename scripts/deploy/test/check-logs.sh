#!/usr/bin/env bash
# Read-only log analysis on the TEST server. Nothing is written, modified, or
# downloaded — output streams straight to your terminal.
#
# Sections (each one short, scannable):
#   1. systemd status + uptime
#   2. journalctl --since <window>   (catches restarts, crashes, OOM kills)
#   3. error.log tail                (gunicorn stderr + Python tracebacks)
#   4. Recent Python tracebacks      (greps with surrounding lines)
#   5. access.log tail               (recent HTTP requests + status)
#   6. Recent HTTP errors            (4xx / 5xx from access.log)
#
# Usage:
#   bash scripts/deploy/test/check-logs.sh           # default: --since 1h
#   bash scripts/deploy/test/check-logs.sh 30m
#   bash scripts/deploy/test/check-logs.sh 2h
#   bash scripts/deploy/test/check-logs.sh '15 minutes ago'
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

# Default window = last 1 hour. Override via $1.
SINCE_RAW="${1:-1 hour ago}"
# Allow shorthand like "30m" / "2h" — translate to journalctl-friendly phrase.
case "$SINCE_RAW" in
  *m) SINCE="${SINCE_RAW%m} minutes ago" ;;
  *h) SINCE="${SINCE_RAW%h} hours ago" ;;
  *d) SINCE="${SINCE_RAW%d} days ago" ;;
  *) SINCE="$SINCE_RAW" ;;
esac

ssh_preflight

log_step "Log analysis · since '$SINCE' · ${SERVER}"

# One SSH session does everything — much faster than 6 separate connects.
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
# Filter noise: keep only systemd lifecycle + ERROR/WARN/CRIT lines so
# casual STARTUP-OK chatter doesn't drown out the real signal.
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
  # Pull every "Traceback (most recent call last):" and the 15 lines after it.
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
  # If grep matched nothing, the pipe still succeeds but prints empty.
  COUNT=$(grep -cE ' (4[0-9][0-9]|5[0-9][0-9])$' "$ACC" 2>/dev/null || echo 0)
  echo "  total in file: $COUNT"
else
  echo "  (no access.log)"
fi

section "Done"
REMOTE
