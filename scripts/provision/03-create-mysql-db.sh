#!/usr/bin/env bash
# Create the instance's MySQL database ($DB_NAME) and user ($DB_USER). Idempotent.
# Persists the generated password to $APP_ROOT/.db_password (chmod 600 root) so
# step 04 can pick it up, and writes $APP_ROOT/.my.cnf so the app user can run
# mysqldump (deploy snapshots, backups).
#
# MySQL administrator access, in order of preference:
#   1. MYSQL_ROOT_PASSWORD (env)                → root@localhost
#   2. /etc/mysql/debian.cnf on the server      → Ubuntu/Debian's maintenance
#      account, root-readable only. Used in place on the server; never copied off.
#   3. otherwise you are prompted for the MySQL root password (hidden).
# The password travels on ssh's stdin, never on a command line (no `ps` exposure).
#
# Multi-instance guard: this step refuses to ALTER a MySQL user it did not create
# (user exists but no $APP_ROOT/.db_password) — on a box where PROD and TEST
# coexist, resetting a shared user's password would break the other instance.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"
require_env SERVER SSH_KEY SSH_USER APP_ROOT APP_USER DB_NAME DB_USER

log_step "03 · Create MySQL database + user ($DB_NAME / $DB_USER)"

ADMIN_MODE=""
if [ -n "${MYSQL_ROOT_PASSWORD:-}" ]; then
  ADMIN_MODE="root-password"
elif [ "$(ssh_run_q "mysql --defaults-file=/etc/mysql/debian.cnf -N -e 'SELECT 1' 2>/dev/null" </dev/null || true)" = "1" ]; then
  ADMIN_MODE="debian-cnf"
  log_info "MySQL admin: the server's maintenance account (/etc/mysql/debian.cnf, root-only, used in place)"
else
  read_secret MYSQL_ROOT_PASSWORD "  MySQL root password (input hidden): "
  ADMIN_MODE="root-password"
fi

# First stdin line = the root password (empty for debian-cnf); the rest = the script.
{ printf '%s\n' "${MYSQL_ROOT_PASSWORD:-}"; cat <<'REMOTE'
set -euo pipefail
PWD_FILE="$APP_ROOT/.db_password"

command -v mysql >/dev/null || { echo "[server] mysql client not installed"; exit 1; }

admin_mysql() {
  if [ "$ADMIN_MODE" = "debian-cnf" ]; then
    mysql --defaults-file=/etc/mysql/debian.cnf "$@"
  else
    MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot "$@"
  fi
}

# Sanity-check admin credentials before we generate the app password
if ! admin_mysql -e "SELECT 1" >/dev/null 2>&1; then
  echo "[server] MySQL admin authentication failed ($ADMIN_MODE). Wrong password?" >&2
  exit 2
fi

# Guard: never touch a MySQL user this instance did not create.
USER_EXISTS=$(admin_mysql -N -e "SELECT COUNT(*) FROM mysql.user WHERE user='$DB_USER' AND host='localhost'")
if [ "$USER_EXISTS" != "0" ] && [ ! -f "$PWD_FILE" ]; then
  echo "[server] MySQL user '$DB_USER'@localhost already exists but $PWD_FILE is missing." >&2
  echo "[server] Refusing to ALTER a user this instance did not create — another instance" >&2
  echo "[server] on this box probably owns it. Pick a distinct DB_USER in env.sh." >&2
  exit 4
fi

# Reuse the app user's password if we generated one previously (idempotent)
if [ -f "$PWD_FILE" ]; then
  DB_PWD=$(cat "$PWD_FILE")
  echo "[server] Reusing existing $DB_USER password at $PWD_FILE"
else
  DB_PWD=$(python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(32)))")
  echo "$DB_PWD" > "$PWD_FILE"
  chmod 600 "$PWD_FILE"
  chown root:root "$PWD_FILE"
  echo "[server] Generated new $DB_USER password → $PWD_FILE (chmod 600 root)"
fi

# DB_PWD is alphanumeric (generated above), so plain quoting is safe.
admin_mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PWD';
ALTER USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PWD';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "[server] DB '$DB_NAME' ready · user '$DB_USER'@localhost has full grants on it (and nothing else)"

# Sanity ping with the new credentials
if MYSQL_PWD="$DB_PWD" mysql -u"$DB_USER" -e "USE \`$DB_NAME\`; SELECT 1" >/dev/null 2>&1; then
  echo "[server] Connectivity verified as $DB_USER"
else
  echo "[server] WARNING: could not connect as $DB_USER. Check admin grants." >&2
  exit 3
fi

# Write $APP_ROOT/.my.cnf so the app user can run mysqldump (backups/snapshots)
cat > "$APP_ROOT/.my.cnf" <<EOF
[client]
host = localhost
user = $DB_USER
password = $DB_PWD
EOF
chmod 600 "$APP_ROOT/.my.cnf"
chown "$APP_USER:$APP_USER" "$APP_ROOT/.my.cnf"
echo "[server] Wrote $APP_ROOT/.my.cnf for backups (chmod 600 $APP_USER:$APP_USER)"
REMOTE
} | ssh_run "ADMIN_MODE='$ADMIN_MODE' APP_ROOT='$APP_ROOT' APP_USER='$APP_USER' DB_NAME='$DB_NAME' DB_USER='$DB_USER' bash -c 'IFS= read -r MYSQL_ROOT_PASSWORD; export MYSQL_ROOT_PASSWORD; exec bash -s'"

log_ok "MySQL DB + user OK"
