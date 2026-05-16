#!/usr/bin/env bash
# Install /etc/nginx/snippets/school.conf and ensure it's included from the
# existing expressonly.in SSL server block. Idempotent. Reloads nginx.
#
# Strategy:
#   - Locate the nginx site file containing `expressonly.in` AND `listen 443`
#   - Use Python to insert `include /etc/nginx/snippets/school.conf;` just
#     before the SSL server block's closing brace.
#   - The Python helper handles every nginx style (separate-line `}`, same-line
#     `}server {`, multiple server blocks per file) by counting brace depth.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"
require_env SERVER SSH_KEY SSH_USER

log_step "06 · Install nginx snippet"

[ -f "$ROOT/deploy/nginx.school.conf" ] || die "deploy/nginx.school.conf missing"

scp_up "$ROOT/deploy/nginx.school.conf" "${SSH_USER}@${SERVER}:/tmp/nginx.school.conf"

ssh_run "bash -s" <<'REMOTE'
set -euo pipefail
mkdir -p /etc/nginx/snippets
mv /tmp/nginx.school.conf /etc/nginx/snippets/school.conf
chown root:root /etc/nginx/snippets/school.conf
chmod 644 /etc/nginx/snippets/school.conf
echo "[server] Wrote /etc/nginx/snippets/school.conf"

# Locate the SSL (port 443) server block file for expressonly.in.
HOST_FILE=""
for f in /etc/nginx/sites-enabled/* /etc/nginx/conf.d/*.conf; do
  [ -f "$f" ] || continue
  case "$f" in *.bak*) continue ;; esac
  if grep -q "expressonly.in" "$f" 2>/dev/null && grep -qE "listen[[:space:]]+443" "$f" 2>/dev/null; then
    HOST_FILE="$f"
    break
  fi
done

if [ -z "$HOST_FILE" ]; then
  echo "[server] WARNING: no nginx server block on :443 references expressonly.in." >&2
  echo "[server] Add this manually to your SSL server { ... } block:" >&2
  echo "           include /etc/nginx/snippets/school.conf;" >&2
  exit 0
fi

echo "[server] Target nginx site: $HOST_FILE"

# Idempotency check
if grep -q "include /etc/nginx/snippets/school.conf" "$HOST_FILE"; then
  echo "[server] include directive already present — skipping insert"
else
  cp "$HOST_FILE" "${HOST_FILE}.bak.$(date +%s)"
  python3 - "$HOST_FILE" <<'PY'
import re, sys
path = sys.argv[1]
src = open(path).read()

# Walk char-by-char. Track brace depth ONLY when we're inside a top-level
# `server { ... }` block. Capture the position of the closing `}` of the
# FIRST server block that contains a `listen <space> 443` directive.
i = 0
n = len(src)
in_server = False
depth = 0          # brace depth inside the current top-level server block
saw_443 = False
block_start = -1
ssl_close_pos = -1
text_buf = []      # body text of current server block (for `listen 443` scan)

while i < n:
    if not in_server:
        # Look for the next `server` keyword followed by optional whitespace and `{`.
        m = re.match(r"server\s*\{", src[i:])
        if m and (i == 0 or not src[i-1].isalnum() and src[i-1] != "_"):
            in_server = True
            depth = 1
            saw_443 = False
            text_buf = []
            block_start = i
            i += m.end()
            continue
        i += 1
    else:
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                body = "".join(text_buf)
                if re.search(r"listen\s+443\b", body) or "ssl" in body.lower() and "listen" in body.lower():
                    if ssl_close_pos == -1:
                        ssl_close_pos = i
                in_server = False
                i += 1
                continue
        text_buf.append(c)
        i += 1

if ssl_close_pos == -1:
    print("[python] No SSL server block found", file=sys.stderr)
    sys.exit(2)

include_line = "    include /etc/nginx/snippets/school.conf;\n"
new_src = src[:ssl_close_pos].rstrip() + "\n" + include_line + src[ssl_close_pos:]
open(path, "w").write(new_src)
print(f"[python] Inserted include before SSL block close at offset {ssl_close_pos}")
PY
  echo "[server] Inserted include into SSL server block in $HOST_FILE (backup at ${HOST_FILE}.bak.*)"
fi

# Test + reload (warnings about conflicting server names are pre-existing — uploadmytds also has them)
nginx -t
systemctl reload nginx
echo "[server] nginx reloaded"
REMOTE

log_ok "nginx snippet installed + reloaded"
