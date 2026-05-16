#!/usr/bin/env bash
# Install OS-level prereqs on the server: python3.12 + venv, build tools for
# pymysql/cryptography, curl, rsync. Idempotent — re-running is a no-op.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/00-common.sh"
require_env SERVER SSH_KEY SSH_USER

log_step "01 · Install prereqs on $SERVER"

ssh_run "bash -s" <<'REMOTE'
set -euo pipefail
need_pkgs=()
have() { dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "install ok installed"; }

for pkg in python3.12 python3.12-venv python3-pip pkg-config default-libmysqlclient-dev curl rsync \
           libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
           fonts-noto-core fonts-guru fonts-noto-color-emoji; do
  if ! have "$pkg"; then
    need_pkgs+=("$pkg")
  fi
done

if [ "${#need_pkgs[@]}" -eq 0 ]; then
  echo "[server] All prereqs present, skipping apt"
  exit 0
fi

# Add deadsnakes PPA only if python3.12 missing on Ubuntu < 24
if ! command -v python3.12 >/dev/null 2>&1; then
  if ! command -v add-apt-repository >/dev/null 2>&1; then
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq software-properties-common
  fi
  if ! grep -qrE "deadsnakes" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null; then
    echo "[server] Adding deadsnakes PPA for python3.12"
    add-apt-repository -y ppa:deadsnakes/ppa
  fi
fi

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${need_pkgs[@]}"
echo "[server] Installed: ${need_pkgs[*]}"
REMOTE

log_ok "Prereqs OK"
