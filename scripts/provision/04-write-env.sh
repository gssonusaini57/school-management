#!/usr/bin/env bash
# Write $APP_ROOT/.env on the server (chmod 600 $APP_USER:$APP_USER).
# Generates JWT_SECRET on the server. Reads the DB password from .db_password.
# Idempotent — does NOT overwrite an existing .env (use --force / FORCE=1 to rewrite).
#
# Email: SMTP_* keys are written ONLY for prod. TEST runs with outbound email
# disabled on purpose — its database is a clone of prod, so the staff rows carry
# real addresses that a test run must never be able to mail.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"
require_env SERVER SSH_KEY SSH_USER ENV APP_ROOT APP_USER DB_NAME DB_USER BASE_URL VITE_BASE

FORCE=${FORCE:-0}
[ "${1:-}" = "--force" ] && FORCE=1
# PROD's .env carries hand-added SMTP credentials and the live JWT secret that
# every issued token is signed with; regenerating it is never routine.
if [ "$ENV" = "prod" ] && [ "$FORCE" = "1" ] && [ "${I_UNDERSTAND_THIS_REWRITES_PROD_ENV:-0}" != "1" ]; then
  die "Refusing FORCE on PROD (.env holds SMTP creds + the live JWT secret). Set I_UNDERSTAND_THIS_REWRITES_PROD_ENV=1 to override."
fi
# Admin SPA base URL (no trailing slash) — reset-password + notification links.
APP_BASE_URL="${BASE_URL}${VITE_BASE%/}"

log_step "04 · Write $APP_ROOT/.env"

ssh_run "FORCE='$FORCE' ENV_NAME='$ENV' APP_ROOT='$APP_ROOT' APP_USER='$APP_USER' DB_NAME='$DB_NAME' DB_USER='$DB_USER' BASE_URL='$BASE_URL' APP_BASE_URL='$APP_BASE_URL' bash -s" <<'REMOTE'
set -euo pipefail
ENV_FILE="$APP_ROOT/.env"
PWD_FILE="$APP_ROOT/.db_password"

if [ -f "$ENV_FILE" ] && [ "${FORCE:-0}" -ne 1 ]; then
  echo "[server] $ENV_FILE already exists (use FORCE=1 to overwrite). Skipping."
  exit 0
fi

[ -f "$PWD_FILE" ] || { echo "[server] $PWD_FILE missing — run step 03 first" >&2; exit 1; }
if [ -f "$ENV_FILE" ]; then
  cp -p "$ENV_FILE" "$ENV_FILE.bak.$(date +%Y%m%d_%H%M%S)"
  echo "[server] Backed up the existing .env before rewriting it"
fi

DB_PWD=$(cat "$PWD_FILE")
JWT_SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(64))")

cat > "$ENV_FILE" <<EOF
DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PWD}@localhost:3306/${DB_NAME}
JWT_SECRET=${JWT_SECRET}
JWT_EXPIRY_HOURS=1
ADMIN_DEFAULT_PASSWORD=admin123
CORS_ORIGINS=${BASE_URL}
LOG_DIR=${APP_ROOT}/logs
BACKUP_DIR=${APP_ROOT}/backups
# Base URL of the admin SPA (no trailing slash) — reset-password + notification links.
APP_BASE_URL=${APP_BASE_URL}
EOF

if [ "$ENV_NAME" = "test" ]; then
  cat >> "$ENV_FILE" <<EOF

# SMTP intentionally unset on TEST — outbound email is disabled so a test run can
# never mail the real staff addresses cloned from prod. (Prod sets SMTP_* here.)
EOF
else
  cat >> "$ENV_FILE" <<EOF

# --- Outbound email (Zoho Mail) — fill in to enable forgot-password + notifications ---
# SMTP_HOST=smtp.zoho.in
# SMTP_PORT=465
# SMTP_USER=info@kisschool.in
# SMTP_PASSWORD=<zoho app password>
# SMTP_USE_SSL=true
# SMTP_FROM=info@kisschool.in
# SMTP_FROM_NAME="Khalsa International School"
# APPROVER_NOTIFY_EMAIL=info@kisschool.in
EOF
fi

chmod 600 "$ENV_FILE"
chown "$APP_USER:$APP_USER" "$ENV_FILE"
echo "[server] Wrote $ENV_FILE (chmod 600 $APP_USER:$APP_USER) · APP_BASE_URL=$APP_BASE_URL"
REMOTE

log_ok ".env written (secrets generated on server, never traversed local disk)"
