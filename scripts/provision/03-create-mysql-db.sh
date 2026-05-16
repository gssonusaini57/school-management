#!/usr/bin/env bash
# Create the school_management MySQL database and `school` user. Idempotent.
# Persists the generated password to /opt/school-management/.db_password (chmod 600 root)
# so step 04 can pick it up. The .env file ends up holding it; this file is
# kept for re-reads if .env is later regenerated.
#
# MYSQL_ROOT_PASSWORD env var is required (provision.sh prompts the user for it).
# Never hardcoded in this repo — root creds belong to the server admin.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"
require_env SERVER SSH_KEY SSH_USER

log_step "03 · Create MySQL database + user"

if [ -z "${MYSQL_ROOT_PASSWORD:-}" ]; then
  read -r -s -p "  MySQL root password (input hidden): " MYSQL_ROOT_PASSWORD; echo
  [ -n "$MYSQL_ROOT_PASSWORD" ] || die "Empty password"
fi

ssh_run "MYSQL_ROOT_PASSWORD='$MYSQL_ROOT_PASSWORD' bash -s" <<'REMOTE'
set -euo pipefail
DB_NAME=school_management
DB_USER=school
PWD_FILE=/opt/school-management/.db_password

command -v mysql >/dev/null || { echo "[server] mysql client not installed"; exit 1; }

# Sanity-check root credentials before we generate the school password
if ! MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -e "SELECT 1" >/dev/null 2>&1; then
  echo "[server] MySQL root authentication failed. Wrong password?" >&2
  exit 2
fi

# Reuse the school user's password if we generated one previously (idempotent)
if [ -f "$PWD_FILE" ]; then
  DB_PWD=$(cat "$PWD_FILE")
  echo "[server] Reusing existing school user password at $PWD_FILE"
else
  DB_PWD=$(python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(32)))")
  echo "$DB_PWD" > "$PWD_FILE"
  chmod 600 "$PWD_FILE"
  chown root:root "$PWD_FILE"
  echo "[server] Generated new school user password → $PWD_FILE (chmod 600 root)"
fi

# Pass DB_PWD to mysql via stdin to avoid shell-quoting headaches with special chars
MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PWD';
ALTER USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PWD';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "[server] DB '$DB_NAME' ready · user '$DB_USER'@localhost has full grants"

# Sanity ping with the new school credentials
if MYSQL_PWD="$DB_PWD" mysql -u"$DB_USER" -e "USE $DB_NAME; SELECT 1" >/dev/null 2>&1; then
  echo "[server] Connectivity verified as $DB_USER"
else
  echo "[server] WARNING: could not connect as $DB_USER. Check root grants." >&2
  exit 3
fi

# Write /opt/school-management/.my.cnf so the school user can run mysqldump
cat > /opt/school-management/.my.cnf <<EOF
[client]
host = localhost
user = $DB_USER
password = $DB_PWD
EOF
chmod 600 /opt/school-management/.my.cnf
chown school:school /opt/school-management/.my.cnf
echo "[server] Wrote /opt/school-management/.my.cnf for backups (chmod 600 school:school)"
REMOTE

log_ok "MySQL DB + user OK"
