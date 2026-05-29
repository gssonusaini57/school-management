#!/usr/bin/env bash
# Deploy the public marketing site (Eleventy → static HTML) to PROD.
# Same as test, with the DEPLOY PROD confirmation gate.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

log_warn "PROD PUBLIC-SITE DEPLOY — server $SERVER, domain $DOMAIN"
read -r -p "Type 'DEPLOY PROD' to confirm: " ans
[ "$ans" = "DEPLOY PROD" ] || die "Aborted"

deploy_public_site_only
