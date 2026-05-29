#!/usr/bin/env bash
# Test environment defaults — sourced by every scripts/deploy/test/*.sh
# All values overridable from caller's environment.
export ENV="test"
export SERVER="${SCHOOL_TEST_SERVER:-104.237.5.113}"
export SSH_USER="${SCHOOL_TEST_SSH_USER:-root}"
export SSH_KEY="${SCHOOL_TEST_SSH_KEY:-$HOME/.ssh/uploadmytds_test}"
export DOMAIN="${SCHOOL_TEST_DOMAIN:-expressonly.in}"

# Subpath layout — TEST shares expressonly.in with uploadmytds, so the whole app
# lives under /school/. These are the historical hardcoded values, now explicit so
# scripts/deploy/common/lib.sh treats test and prod uniformly (PROD overrides them
# in prod/env.sh to serve at the domain root).
export VITE_BASE="/school/admin/"
export VITE_API_URL="/school/api"
export SITE_BASE_PATH="/school"
export HEALTH_PATH="/school/api/health"
export SITE_URL_PATH="/school/"
