#!/usr/bin/env bash
# Deploy backend (FastAPI + Alembic) to the TEST server.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

deploy_backend_only
