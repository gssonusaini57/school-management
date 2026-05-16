#!/usr/bin/env bash
# Deploy frontend to PROD. Same as test, with confirmation.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

log_warn "PROD FRONTEND DEPLOY — server $SERVER, domain $DOMAIN"
read -r -p "Type 'DEPLOY PROD' to confirm: " ans
[ "$ans" = "DEPLOY PROD" ] || die "Aborted"

deploy_frontend_only
