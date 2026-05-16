#!/usr/bin/env bash
# Deploy backend (FastAPI + Alembic) to PROD.
# Requires explicit confirmation. Same code path as test — only env.sh differs.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

log_warn "PROD DEPLOY — server $SERVER, domain $DOMAIN"
read -r -p "Type 'DEPLOY PROD' to confirm: " ans
[ "$ans" = "DEPLOY PROD" ] || die "Aborted"

deploy_backend_only
