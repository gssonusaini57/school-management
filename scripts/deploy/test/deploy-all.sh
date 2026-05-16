#!/usr/bin/env bash
# Deploy backend + frontend to the TEST server in one go (with snapshot+rollback).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

deploy_full
