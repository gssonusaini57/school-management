#!/usr/bin/env bash
# Production environment defaults — sourced by every scripts/deploy/prod/*.sh
# Override via SCHOOL_PROD_* env vars when you have a real prod box.
#
# WHEN YOU GO TO PROD:
#   1. Edit the defaults below (SERVER, DOMAIN, key path)
#   2. Generate a separate SSH key: ssh-keygen -t ed25519 -f ~/.ssh/school-management_prod
#   3. ssh-copy-id -i ~/.ssh/school-management_prod.pub root@<prod-server>
#   4. Run: SERVER=<prod-server> SSH_KEY=~/.ssh/school-management_prod \
#           DOMAIN=<prod-domain> bash scripts/provision/provision.sh
#   5. Then: bash scripts/deploy/prod/deploy-all.sh
export ENV="prod"
export SERVER="${SCHOOL_PROD_SERVER:-CHANGE_ME_PROD_IP}"
export SSH_USER="${SCHOOL_PROD_SSH_USER:-root}"
export SSH_KEY="${SCHOOL_PROD_SSH_KEY:-$HOME/.ssh/school-management_prod}"
export DOMAIN="${SCHOOL_PROD_DOMAIN:-CHANGE_ME_PROD_DOMAIN}"

# Safety guard — refuse to run prod scripts before the user actually configures them.
if [ "$SERVER" = "CHANGE_ME_PROD_IP" ] || [ "$DOMAIN" = "CHANGE_ME_PROD_DOMAIN" ]; then
  printf "\033[31m✗\033[0m  Prod env not configured yet. Edit scripts/deploy/prod/env.sh first.\n" >&2
  exit 2
fi
