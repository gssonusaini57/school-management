#!/usr/bin/env bash
# Common helpers for provisioning + deploy scripts. Source this, don't run it.
# Reads SERVER, SSH_KEY, SSH_USER from caller's env.

set -euo pipefail

# ── Color logging ──────────────────────────────────────────────────────────
log_info()  { printf "\033[34m▶\033[0m  %s\n" "$*"; }
log_step()  { printf "\n\033[36m━━ %s ━━\033[0m\n" "$*"; }
log_ok()    { printf "\033[32m✓\033[0m  %s\n" "$*"; }
log_warn()  { printf "\033[33m!\033[0m  %s\n" "$*"; }
log_err()   { printf "\033[31m✗\033[0m  %s\n" "$*" >&2; }
die()       { log_err "$*"; exit 1; }

# ── Required env ───────────────────────────────────────────────────────────
require_env() {
  local missing=0
  for v in "$@"; do
    if [ -z "${!v:-}" ]; then log_err "Missing env: $v"; missing=1; fi
  done
  [ $missing -eq 0 ] || die "Set required env vars and retry"
}

# ── SSH wrappers ───────────────────────────────────────────────────────────
ssh_run() {
  ssh -i "$SSH_KEY" \
      -o StrictHostKeyChecking=accept-new \
      -o ConnectTimeout=10 \
      "${SSH_USER}@${SERVER}" "$@"
}

ssh_run_q() {
  # Quiet variant — suppresses banners/MOTD, useful for short outputs we capture
  ssh -i "$SSH_KEY" \
      -o StrictHostKeyChecking=accept-new \
      -o LogLevel=ERROR \
      -o ConnectTimeout=10 \
      "${SSH_USER}@${SERVER}" "$@"
}

scp_up() {
  rsync -az --human-readable -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" "$@"
}

scp_down() {
  rsync -az --human-readable -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" "$@"
}

# ── Confirmation prompt ────────────────────────────────────────────────────
confirm() {
  local prompt="${1:-Proceed?} [y/N] "
  local ans
  read -r -p "$prompt" ans
  [[ "$ans" =~ ^[Yy]$ ]] || die "Aborted by user"
}

# ── Verify SSH connectivity early ──────────────────────────────────────────
ssh_preflight() {
  log_info "Testing SSH to ${SSH_USER}@${SERVER} (key: ${SSH_KEY})…"
  if ! ssh_run_q "echo ok" >/dev/null 2>&1; then
    die "SSH connect failed. Check key, server IP, and authorized_keys."
  fi
  log_ok "SSH reachable"
}
