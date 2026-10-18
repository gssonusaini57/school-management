#!/usr/bin/env bash
# One-shot provisioning entrypoint for ONE instance of the app on a server.
# Usage:
#   bash scripts/provision/provision.sh [--inspect-only] [--force-env]      # ENV=test (default)
#   ENV=prod bash scripts/provision/provision.sh …                          # prod instance
#
# All values (server, key, domain, install dir, system user, unit, port, DB) come
# from scripts/deploy/$ENV/env.sh — PROD and TEST are two instances on the same
# box, so nothing here is hardcoded. Override via SCHOOL_<ENV>_* vars if needed.
#
# Interactive: asks for confirmation (ASSUME_YES=1 answers it). MySQL admin access
# for step 03 comes from MYSQL_ROOT_PASSWORD, else the server's own
# /etc/mysql/debian.cnf, else a hidden prompt — never stored anywhere.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"

ENV="${ENV:-test}"
ENV_FILE="$HERE/../deploy/$ENV/env.sh"
[ -f "$ENV_FILE" ] || die "No such environment: $ENV (expected $ENV_FILE)"
# shellcheck disable=SC1090
source "$ENV_FILE"
require_env SERVER SSH_USER SSH_KEY DOMAIN BASE_URL APP_ROOT APP_USER SERVICE_NAME APP_PORT DB_NAME DB_USER
validate_layout

INSPECT_ONLY=0
FORCE_ENV=0
for arg in "$@"; do
  case "$arg" in
    --inspect-only) INSPECT_ONLY=1 ;;
    --force-env)    FORCE_ENV=1 ;;
    *) die "Unknown arg: $arg" ;;
  esac
done

log_step "Pre-flight inspection of $SERVER for ENV=$ENV (read-only)"
ssh_preflight

ssh_run "DOMAIN='$DOMAIN' APP_ROOT='$APP_ROOT' APP_USER='$APP_USER' SERVICE_NAME='$SERVICE_NAME' APP_PORT='$APP_PORT' NGINX_SNIPPET='${NGINX_SNIPPET:-}' bash -s" <<'REMOTE'
set -u
echo "── OS ────────────────────────────────────────────────"
. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" || uname -a
echo
echo "── Existing services ─────────────────────────────────"
for svc in nginx mysql tomcat school-management "$SERVICE_NAME"; do
  state=$(systemctl is-active "$svc" 2>/dev/null || true)
  printf "  %-26s %s\n" "$svc" "${state:-unknown}"
done
echo
echo "── Versions ──────────────────────────────────────────"
mysql --version 2>/dev/null || echo "  mysql client: missing"
nginx -v 2>&1 | sed 's/^/  /' || echo "  nginx: missing"
python3.12 --version 2>/dev/null | sed 's/^/  /' || echo "  python3.12: NOT YET (provisioning will install)"
echo
echo "── Port 127.0.0.1:$APP_PORT (must be free for this instance) ─"
IN_USE=$(ss -ltnp 2>/dev/null | grep -E ":${APP_PORT}[[:space:]]" || true)
if [ -n "$IN_USE" ]; then printf '%s\n' "$IN_USE" | sed 's/^/  IN USE: /'; else echo "  free"; fi
echo
echo "── nginx conf with 'server_name … $DOMAIN' (target for the include) ─"
grep -lE "^[[:space:]]*server_name[^;]*[[:space:]]${DOMAIN//./\\.}([[:space:];]|$)" /etc/nginx/sites-enabled/* /etc/nginx/conf.d/*.conf 2>/dev/null | sed 's/^/  /' || echo "  (none found)"
echo
echo "── existing $APP_ROOT/ ───────────────────────────────"
[ -d "$APP_ROOT" ] && ls -la "$APP_ROOT/" | head -20 || echo "  (does not exist)"
echo
echo "── system user $APP_USER ─────────────────────────────"
id "$APP_USER" 2>/dev/null || echo "  (does not exist)"
echo
echo "── existing ${SERVICE_NAME}.service ──────────────────"
[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ] && echo "  installed" || echo "  not installed"
echo
echo "── existing nginx snippets ───────────────────────────"
ls /etc/nginx/snippets/ 2>/dev/null | sed 's/^/  /' || echo "  (no snippets dir)"
[ -n "$NGINX_SNIPPET" ] && { [ -f "$NGINX_SNIPPET" ] && echo "  → $NGINX_SNIPPET: present" || echo "  → $NGINX_SNIPPET: not yet installed"; }
REMOTE

echo
log_warn "Review the inspection output above carefully."
log_info "ENV=$ENV · Server: $SERVER · SSH key: $SSH_KEY · URL: ${BASE_URL}${URL_PREFIX:-}/admin/"
log_info "Will create: system user '$APP_USER', $APP_ROOT/, MySQL DB '$DB_NAME' + user '$DB_USER', .env, systemd unit '$SERVICE_NAME' (gunicorn 127.0.0.1:$APP_PORT)"
if [ -n "${NGINX_SNIPPET:-}" ]; then
  log_info "nginx: install $NGINX_SNIPPET and append ONE include line to the 'server_name $DOMAIN' block (backup kept, nginx -t gated)."
else
  log_info "nginx: skipped (standalone vhost deploy/nginx.kisschool.conf is installed by hand for this ENV)."
fi
log_info "Other instances, the enamfoss app, MySQL itself and existing nginx blocks are NOT otherwise touched."

if [ "$INSPECT_ONLY" -eq 1 ]; then
  log_ok "Inspection complete (--inspect-only)"
  exit 0
fi

confirm "Proceed with provisioning ENV=$ENV on $SERVER?"

# MySQL admin access is resolved by step 03 (MYSQL_ROOT_PASSWORD if exported,
# else the server's /etc/mysql/debian.cnf, else a hidden prompt).

bash "$HERE/01-install-prereqs.sh"
bash "$HERE/02-create-user-dirs.sh"
bash "$HERE/03-create-mysql-db.sh"
FORCE="$FORCE_ENV" bash "$HERE/04-write-env.sh"
bash "$HERE/05-install-systemd.sh"
bash "$HERE/06-install-nginx-snippet.sh"

log_step "Provisioning summary"
ssh_run "APP_ROOT='$APP_ROOT' APP_USER='$APP_USER' SERVICE_NAME='$SERVICE_NAME' DB_NAME='$DB_NAME' NGINX_SNIPPET='${NGINX_SNIPPET:-}' bash -s" <<'REMOTE'
echo "── Final state ───────────────────────────────────────"
id "$APP_USER"
ls -ld "$APP_ROOT"/{app,frontend/dist,logs,backups}
[ -f "$APP_ROOT/.env" ] && echo ".env: $(stat -c '%a %U:%G' "$APP_ROOT/.env") (contents redacted)"
mysql --defaults-file="$APP_ROOT/.my.cnf" -N -e "SELECT CONCAT('database: ', SCHEMA_NAME) FROM information_schema.schemata WHERE SCHEMA_NAME='$DB_NAME'" 2>/dev/null || echo "(could not query $DB_NAME with $APP_ROOT/.my.cnf)"
systemctl is-enabled "$SERVICE_NAME"
if [ -n "$NGINX_SNIPPET" ]; then echo "Snippet: $(ls "$NGINX_SNIPPET" 2>/dev/null || echo MISSING)"; fi
nginx -t 2>&1 | sed 's/^/  /'
REMOTE

log_ok "Provisioning complete. Next: bash scripts/deploy/$ENV/deploy-all.sh"
