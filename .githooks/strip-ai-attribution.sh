#!/bin/sh
# Reads a commit message on stdin, writes it back with AI attribution trailers
# removed. Companion to no-ai-attribution.sh, for cleaning up history that was
# committed before the guardrail existed.
#
#   git filter-branch -f --msg-filter '.githooks/strip-ai-attribution.sh' <range>
#
# It does NOT carry its own copy of the patterns: it feeds each line to
# no-ai-attribution.sh and drops the lines that one rejects. One rule, one
# file — a pattern added there is honoured here for free.
#
# Trailing blank lines left behind by a removed trailer are collapsed, so the
# message ends in exactly one newline.

CHECK="$(dirname "$0")/no-ai-attribution.sh"
[ -x "$CHECK" ] || { echo "strip-ai-attribution: missing $CHECK" >&2; exit 1; }

kept=$(
  while IFS= read -r line || [ -n "$line" ]; do
    if printf '%s\n' "$line" | "$CHECK" loose >/dev/null 2>&1; then
      printf '%s\n' "$line"
    fi
  done
)

# Strip trailing blank lines, then emit with a single final newline.
printf '%s\n' "$kept" | awk '
  { buf[NR] = $0 }
  END {
    last = 0
    for (i = 1; i <= NR; i++) if (buf[i] ~ /[^[:space:]]/) last = i
    for (i = 1; i <= last; i++) print buf[i]
  }'
