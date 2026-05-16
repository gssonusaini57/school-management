#!/usr/bin/env bash
# Test environment defaults — sourced by every scripts/deploy/test/*.sh
# All values overridable from caller's environment.
export ENV="test"
export SERVER="${SCHOOL_TEST_SERVER:-104.237.5.113}"
export SSH_USER="${SCHOOL_TEST_SSH_USER:-root}"
export SSH_KEY="${SCHOOL_TEST_SSH_KEY:-$HOME/.ssh/uploadmytds_test}"
export DOMAIN="${SCHOOL_TEST_DOMAIN:-expressonly.in}"
