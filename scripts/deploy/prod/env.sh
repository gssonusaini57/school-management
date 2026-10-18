#!/usr/bin/env bash
# Production environment defaults — sourced by every scripts/deploy/prod/*.sh and
# by scripts/provision/provision.sh when ENV=prod. Override via SCHOOL_PROD_* env vars.
#
# PROD = https://kisschool.in served at the domain ROOT on 69.62.72.137 (shared box:
# also hosts the enamfoss Tomcat app AND, since 2026-10, the TEST instance of this
# very app under /kisschool/ — see scripts/deploy/test/env.sh). Every value below
# that names a server resource is the ORIGINAL single-instance layout; TEST uses
# the same knobs with suffixed names so the two never collide.
export ENV="prod"
export SERVER="${SCHOOL_PROD_SERVER:-69.62.72.137}"
export SSH_USER="${SCHOOL_PROD_SSH_USER:-root}"
export SSH_KEY="${SCHOOL_PROD_SSH_KEY:-$HOME/.ssh/enamfoss_prod}"
export DOMAIN="${SCHOOL_PROD_DOMAIN:-kisschool.in}"
export BASE_URL="${SCHOOL_PROD_BASE_URL:-https://kisschool.in}"

# ── URL layout — PROD serves the app at the apex root (empty prefix) ─────────
export URL_PREFIX=""
export VITE_BASE="/admin/"           # Vite base → SPA at https://kisschool.in/admin/
export VITE_API_URL="/api"           # axios baseURL (overrides frontend/.env.production)
export HEALTH_PATH="/api/health"     # health-check path used by deploy scripts
export SITE_URL_PATH="/"             # public-site URL printed on success
export SITE_BASE_PATH=""             # Eleventy public site at the apex root
export PUBLIC_SITE="1"               # PROD has the public marketing site
export DOWNLOADS_URL="${BASE_URL}${URL_PREFIX}/downloads"
export APK_LOCAL_NAME="kis-attendance.apk"   # scripts/build-android.sh prod output (gitignored)
export MANIFEST_NAME="app-version.json"      # force-update manifest the prod app polls

# ── Instance knobs (the un-suffixed originals) ──────────────────────────────
export APP_ROOT="/opt/school-management"
export APP_USER="school"
export SERVICE_NAME="school-management"
export APP_PORT="8000"
export DB_NAME="school_management"
export DB_USER="school"
# PROD's nginx is the standalone vhost deploy/nginx.kisschool.conf (installed by
# hand to /etc/nginx/conf.d/kisschool.conf) — empty means provisioning step 06 skips.
export NGINX_SNIPPET=""

# Safety guard — refuse to run prod scripts before the user actually configures them.
if [ "$SERVER" = "CHANGE_ME_PROD_IP" ] || [ "$DOMAIN" = "CHANGE_ME_PROD_DOMAIN" ]; then
  printf "\033[31m✗\033[0m  Prod env not configured yet. Edit scripts/deploy/prod/env.sh first.\n" >&2
  exit 2
fi
