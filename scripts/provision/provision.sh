#!/usr/bin/env bash
# One-shot provisioning entrypoint.
# Usage:
#   bash scripts/provision/provision.sh [--inspect-only] [--force-env]
#
# Required env (or args at top of file):
#   SERVER, SSH_KEY, SSH_USER, DOMAIN
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"

# Defaults — override via env when targeting prod or a different test box.
SERVER="${SERVER:-104.237.5.113}"
SSH_USER="${SSH_USER:-root}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/uploadmytds_test}"
DOMAIN="${DOMAIN:-expressonly.in}"

INSPECT_ONLY=0
FORCE_ENV=0
for arg in "$@"; do
  case "$arg" in
    --inspect-only) INSPECT_ONLY=1 ;;
    --force-env)    FORCE_ENV=1 ;;
    *) die "Unknown arg: $arg" ;;
  esac
done

export SERVER SSH_USER SSH_KEY DOMAIN

log_step "Pre-flight inspection of $SERVER (read-only)"
ssh_preflight

ssh_run "bash -s" <<'REMOTE'
set -u
echo "── OS ────────────────────────────────────────────────"
. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" || uname -a
echo
echo "── Existing services ─────────────────────────────────"
for svc in nginx mysql tomcat school-management; do
  state=$(systemctl is-active "$svc" 2>/dev/null || echo "absent")
  printf "  %-20s %s\n" "$svc" "$state"
done
echo
echo "── Versions ──────────────────────────────────────────"
mysql --version 2>/dev/null || echo "  mysql client: missing"
nginx -v 2>&1 | sed 's/^/  /' || echo "  nginx: missing"
python3.12 --version 2>/dev/null | sed 's/^/  /' || echo "  python3.12: NOT YET (provisioning will install)"
echo
echo "── nginx server-block sites for expressonly.in ───────"
grep -l expressonly.in /etc/nginx/sites-enabled/* /etc/nginx/conf.d/*.conf 2>/dev/null || echo "  (none found)"
echo
echo "── existing /opt/school-management/ ──────────────────"
[ -d /opt/school-management ] && ls -la /opt/school-management/ | head -20 || echo "  (does not exist)"
echo
echo "── existing school-management.service ────────────────"
[ -f /etc/systemd/system/school-management.service ] && echo "  installed" || echo "  not installed"
echo
echo "── existing nginx snippets ───────────────────────────"
ls /etc/nginx/snippets/ 2>/dev/null | sed 's/^/  /' || echo "  (no snippets dir)"
REMOTE

echo
log_warn "Review the inspection output above carefully."
log_info "Server: $SERVER · SSH key: $SSH_KEY · Domain: $DOMAIN"
log_info "Will install: python3.12 (if missing), system user 'school', /opt/school-management/, MySQL DB+user, .env, systemd unit, nginx /school/ snippet."
log_info "Existing uploadmytds, MySQL, and nginx server blocks are NOT touched."

if [ "$INSPECT_ONLY" -eq 1 ]; then
  log_ok "Inspection complete (--inspect-only)"
  exit 0
fi

confirm "Proceed with provisioning?"

# Prompt once for the MySQL root password (only used by step 03; never stored).
if [ -z "${MYSQL_ROOT_PASSWORD:-}" ]; then
  read -r -s -p "  MySQL root password (input hidden, used only for step 03): " MYSQL_ROOT_PASSWORD; echo
  [ -n "$MYSQL_ROOT_PASSWORD" ] || die "MYSQL_ROOT_PASSWORD is required"
fi
export MYSQL_ROOT_PASSWORD

bash "$HERE/01-install-prereqs.sh"
bash "$HERE/02-create-user-dirs.sh"
bash "$HERE/03-create-mysql-db.sh"
FORCE="$FORCE_ENV" DOMAIN="$DOMAIN" bash "$HERE/04-write-env.sh"
bash "$HERE/05-install-systemd.sh"
bash "$HERE/06-install-nginx-snippet.sh"

log_step "Provisioning summary"
ssh_run "bash -s" <<'REMOTE'
echo "── Final state ───────────────────────────────────────"
id school
ls -ld /opt/school-management/{app,frontend/dist,logs,backups}
[ -f /opt/school-management/.env ] && echo ".env: $(stat -c '%a %U:%G' /opt/school-management/.env) (contents redacted)"
mysql -uroot --protocol=socket -e "SHOW DATABASES;" 2>/dev/null | grep school_management || echo "(could not list DBs — check root auth)"
systemctl is-enabled school-management
echo "Snippet: $(ls /etc/nginx/snippets/school.conf 2>/dev/null || echo MISSING)"
nginx -t 2>&1 | sed 's/^/  /'
REMOTE

log_ok "Provisioning complete. Next: bash scripts/deploy/test/deploy-all.sh"
