#!/usr/bin/env bash
# Write /opt/school-management/.env on the server (chmod 600 school:school).
# Generates JWT_SECRET on the server. Reads DB password from .db_password.
# Idempotent — does NOT overwrite an existing .env (use --force to rewrite).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"
require_env SERVER SSH_KEY SSH_USER

FORCE=${FORCE:-0}
[ "${1:-}" = "--force" ] && FORCE=1
DOMAIN_OVERRIDE=${DOMAIN:-expressonly.in}

log_step "04 · Write /opt/school-management/.env"

ssh_run "DOMAIN='$DOMAIN_OVERRIDE' FORCE='$FORCE' bash -s" <<'REMOTE'
set -euo pipefail
ENV_FILE=/opt/school-management/.env
PWD_FILE=/opt/school-management/.db_password

if [ -f "$ENV_FILE" ] && [ "${FORCE:-0}" -ne 1 ]; then
  echo "[server] $ENV_FILE already exists (use FORCE=1 to overwrite). Skipping."
  exit 0
fi

[ -f "$PWD_FILE" ] || { echo "[server] $PWD_FILE missing — run step 03 first" >&2; exit 1; }

DB_PWD=$(cat "$PWD_FILE")
JWT_SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(64))")

cat > "$ENV_FILE" <<EOF
DATABASE_URL=mysql+pymysql://school:${DB_PWD}@localhost:3306/school_management
JWT_SECRET=${JWT_SECRET}
JWT_EXPIRY_HOURS=8
ADMIN_DEFAULT_PASSWORD=admin123
CORS_ORIGINS=https://${DOMAIN}
LOG_DIR=/opt/school-management/logs
BACKUP_DIR=/opt/school-management/backups
EOF
chmod 600 "$ENV_FILE"
chown school:school "$ENV_FILE"
echo "[server] Wrote $ENV_FILE (chmod 600 school:school)"
REMOTE

log_ok ".env written (secrets generated on server, never traversed local disk)"
