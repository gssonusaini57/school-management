#!/usr/bin/env bash
# TEST environment — sourced by every scripts/deploy/test/*.sh and by
# scripts/provision/provision.sh (ENV=test). Connection values are overridable via
# SCHOOL_TEST_* env vars; the layout + instance knobs below are the single source
# of truth for everything the scripts and templates need to know about TEST.
#
# TEST lives on the SAME box as PROD (69.62.72.137) as a second, fully separate
# instance: own install dir, system user, systemd unit, gunicorn port, MySQL DB +
# user and nginx snippet. It is reachable over plain HTTP on the bare IP under the
# /kisschool/ prefix (the bare-IP :80 vhost belongs to the enamfoss app; we only
# add one `include` line to it):
#   http://69.62.72.137/kisschool/admin/      → React staff portal
#   http://69.62.72.137/kisschool/api/        → FastAPI (gunicorn 127.0.0.1:8001)
#   http://69.62.72.137/kisschool/downloads/  → staging APK + app-version-test.json
# There is NO public marketing site on TEST.
export ENV="test"
export SERVER="${SCHOOL_TEST_SERVER:-69.62.72.137}"
export SSH_USER="${SCHOOL_TEST_SSH_USER:-root}"
export SSH_KEY="${SCHOOL_TEST_SSH_KEY:-$HOME/.ssh/enamfoss_prod}"
# nginx server_name whose server { } block receives our `include` line.
export DOMAIN="${SCHOOL_TEST_DOMAIN:-69.62.72.137}"
# scheme + host for health checks, APK verification, CORS_ORIGINS and APP_BASE_URL.
export BASE_URL="${SCHOOL_TEST_BASE_URL:-http://69.62.72.137}"

# ── URL layout — everything derives from one prefix ─────────────────────────
export URL_PREFIX="/kisschool"
export VITE_BASE="${URL_PREFIX}/admin/"        # Vite base → SPA at ${BASE_URL}${URL_PREFIX}/admin/
export VITE_API_URL="${URL_PREFIX}/api"        # axios baseURL (overrides frontend/.env.production)
export HEALTH_PATH="${URL_PREFIX}/api/health"  # health-check path used by the deploy scripts
export SITE_URL_PATH="${URL_PREFIX}/admin/"    # URL printed on success
export SITE_BASE_PATH="${URL_PREFIX}"          # unused on TEST (no public site) — kept for lib.sh parity
export PUBLIC_SITE="0"                         # 0 → the public-site deploy refuses to run for TEST
export DOWNLOADS_URL="${BASE_URL}${URL_PREFIX}/downloads"
export APK_LOCAL_NAME="kis-attendance-test.apk"  # scripts/build-android.sh test output (gitignored)
export MANIFEST_NAME="app-version-test.json"     # force-update manifest the staging app polls

# ── Second-instance knobs (PROD on the same box owns the un-suffixed names) ──
export APP_ROOT="/opt/school-management-test"
export APP_USER="school-test"
export SERVICE_NAME="school-management-test"
export APP_PORT="8001"
export DB_NAME="school_management_test"
export DB_USER="school_test"
export NGINX_SNIPPET="/etc/nginx/snippets/${SERVICE_NAME}.conf"
