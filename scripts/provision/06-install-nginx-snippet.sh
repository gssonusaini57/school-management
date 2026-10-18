#!/usr/bin/env bash
# Install this instance's nginx snippet ($NGINX_SNIPPET, rendered from
# deploy/nginx.school-test.conf) and make sure it is `include`d from the EXISTING
# server { } block whose server_name lists $DOMAIN. Idempotent. Reloads nginx.
#
# Skipped when NGINX_SNIPPET is empty (PROD: standalone vhost deploy/nginx.kisschool.conf).
#
# Strategy:
#   - Find the ONE nginx conf file with a `server_name` directive listing $DOMAIN as
#     a whole token (any listen port — on 69.62.72.137 that is the enamfoss bare-IP
#     :80 vhost). Zero or several matches → stop with an error.
#   - A Python helper inserts `include $NGINX_SNIPPET;` just before the closing brace
#     of THAT server block (brace-depth walk; comments are ignored while scanning).
#   - The host file is backed up to /etc/nginx/backups/ first; if `nginx -t` fails
#     the backup is restored, so a broken file is never left for the next reload
#     (e.g. certbot's renewal hook) to trip over.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"
require_env SERVER SSH_KEY SSH_USER DOMAIN APP_ROOT APP_PORT

log_step "06 · Install nginx snippet"

if [ -z "${NGINX_SNIPPET:-}" ]; then
  log_warn "NGINX_SNIPPET is empty for ENV=${ENV:-?} — this instance uses a standalone vhost; nothing to do."
  exit 0
fi
[ -n "${URL_PREFIX:-}" ] || die "URL_PREFIX is empty — the snippet layout needs a prefix (a root layout needs a standalone vhost like deploy/nginx.kisschool.conf)"

TEMPLATE="$ROOT/deploy/nginx.school-test.conf"
[ -f "$TEMPLATE" ] || die "deploy/nginx.school-test.conf missing"

RENDERED="$(mktemp)"
trap 'rm -f "$RENDERED"' EXIT
render_template "$TEMPLATE" "$RENDERED"

scp_up "$RENDERED" "${SSH_USER}@${SERVER}:/tmp/nginx-snippet.conf"

ssh_run "DOMAIN='$DOMAIN' NGINX_SNIPPET='$NGINX_SNIPPET' bash -s" <<'REMOTE'
set -euo pipefail
mkdir -p /etc/nginx/snippets /etc/nginx/backups
SNIP_BAK=""
if [ -f "$NGINX_SNIPPET" ]; then
  SNIP_BAK="/etc/nginx/backups/$(basename "$NGINX_SNIPPET").$(date +%s)"
  cp -p "$NGINX_SNIPPET" "$SNIP_BAK"
fi
mv /tmp/nginx-snippet.conf "$NGINX_SNIPPET"
chown root:root "$NGINX_SNIPPET"
chmod 644 "$NGINX_SNIPPET"
echo "[server] Wrote $NGINX_SNIPPET"

# Locate the conf file(s) whose server_name lists $DOMAIN as a whole token.
DOMAIN_RE=$(printf '%s' "$DOMAIN" | sed 's/\./\\./g')
MATCHES=()
for f in /etc/nginx/sites-enabled/* /etc/nginx/conf.d/*.conf; do
  [ -f "$f" ] || continue
  case "$f" in *.bak*) continue ;; esac
  if grep -qE "^[[:space:]]*server_name[^;#]*[[:space:]]${DOMAIN_RE}([[:space:];]|$)" "$f" 2>/dev/null; then
    MATCHES+=("$f")
  fi
done

if [ "${#MATCHES[@]}" -ne 1 ]; then
  echo "[server] ERROR: expected exactly one nginx conf with 'server_name … $DOMAIN', found ${#MATCHES[@]}: ${MATCHES[*]:-none}" >&2
  echo "[server] Snippet is installed but NOT included. Add manually inside the right server { } block:" >&2
  echo "           include $NGINX_SNIPPET;" >&2
  exit 1
fi
HOST_FILE="${MATCHES[0]}"
echo "[server] Target nginx conf: $HOST_FILE"

INCLUDE_LINE="include $NGINX_SNIPPET;"
HOST_BAK=""
if grep -qF "$INCLUDE_LINE" "$HOST_FILE"; then
  echo "[server] include directive already present — skipping insert"
else
  HOST_BAK="/etc/nginx/backups/$(basename "$HOST_FILE").$(date +%s)"
  cp -p "$HOST_FILE" "$HOST_BAK"
  python3 - "$HOST_FILE" "$DOMAIN" "$NGINX_SNIPPET" <<'PY'
import re, sys, os
path, domain, snippet = sys.argv[1:4]
src = open(path).read()
# Blank out comments (same length → offsets stay valid) so braces or
# server_name text inside comments can't confuse the scan.
scan = re.sub(r"#[^\n]*", lambda m: " " * len(m.group(0)), src)

dom_re = re.compile(r"(?:^|[;{\s])server_name\b[^;]*?(?<![\w.-])" + re.escape(domain) + r"(?![\w.-])")
hits, i, n = [], 0, len(scan)
while i < n:
    m = re.compile(r"(?<![\w-])server\s*\{").search(scan, i)
    if not m:
        break
    depth, j = 1, m.end()
    while j < n and depth:
        if scan[j] == "{":
            depth += 1
        elif scan[j] == "}":
            depth -= 1
        j += 1
    if depth:
        print(f"[python] Unbalanced braces in {path}", file=sys.stderr); sys.exit(2)
    close = j - 1                       # offset of this server block's closing brace
    if dom_re.search(scan[m.end():close]):
        hits.append(close)
    i = j

if len(hits) != 1:
    print(f"[python] Expected 1 server block with server_name {domain} in {path}, found {len(hits)}", file=sys.stderr)
    sys.exit(3)

close = hits[0]
new_src = src[:close].rstrip() + "\n\n    " + f"include {snippet};" + "\n" + src[close:]
tmp = path + ".tmp-insert"
with open(tmp, "w") as fh:
    fh.write(new_src)
os.chmod(tmp, os.stat(path).st_mode & 0o777)
os.replace(tmp, path)
print(f"[python] Inserted 'include {snippet};' before the closing brace of the server_name {domain} block")
PY
  echo "[server] Backup of the original: $HOST_BAK"
fi

if ! nginx -t; then
  echo "[server] nginx -t FAILED — restoring backups" >&2
  [ -n "$HOST_BAK" ] && cp -p "$HOST_BAK" "$HOST_FILE"
  if [ -n "$SNIP_BAK" ]; then cp -p "$SNIP_BAK" "$NGINX_SNIPPET"; else rm -f "$NGINX_SNIPPET"; fi
  nginx -t || true
  exit 1
fi
systemctl reload nginx
echo "[server] nginx reloaded"
REMOTE

log_ok "nginx snippet installed + included + reloaded"
