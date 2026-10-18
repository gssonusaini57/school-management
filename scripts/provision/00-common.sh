#!/usr/bin/env bash
# Common helpers for provisioning + deploy scripts. Source this, don't run it.
# Reads SERVER, SSH_KEY, SSH_USER from caller's env (set by scripts/deploy/<env>/env.sh).

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

# ── Prompts ────────────────────────────────────────────────────────────────
# Both read from the terminal directly when one is available, so an earlier ssh
# call that drained stdin (or a piped stdin) can't auto-answer them.
# ASSUME_YES=1 answers `confirm` with yes (for non-interactive runs whose intent
# was already confirmed elsewhere); it never supplies a secret.
confirm() {
  local prompt="${1:-Proceed?} [y/N] "
  local ans=""
  if [ "${ASSUME_YES:-0}" = "1" ]; then
    log_warn "${1:-Proceed?} → yes (ASSUME_YES=1)"
    return 0
  fi
  if { true </dev/tty; } 2>/dev/null; then
    read -r -p "$prompt" ans </dev/tty || true
  else
    read -r -p "$prompt" ans || true
  fi
  [[ "$ans" =~ ^[Yy]$ ]] || die "Aborted by user"
}

# read_secret VAR "prompt" — hidden input into VAR (bash 3.2-safe).
read_secret() {
  local __val=""
  if { true </dev/tty; } 2>/dev/null; then
    read -r -s -p "$2" __val </dev/tty || true
  else
    read -r -s -p "$2" __val || true
  fi
  echo
  [ -n "$__val" ] || die "Empty input for $1"
  printf -v "$1" '%s' "$__val"
}

# ── Verify SSH connectivity early ──────────────────────────────────────────
ssh_preflight() {
  log_info "Testing SSH to ${SSH_USER}@${SERVER} (key: ${SSH_KEY})…"
  # </dev/null: never read our stdin (keeps piped input / heredocs for the caller).
  # (ssh options can't go after ssh_run's host argument, so no `-n` here.)
  if ! ssh_run_q "echo ok" </dev/null >/dev/null 2>&1; then
    die "SSH connect failed. Check key, server IP, and authorized_keys."
  fi
  log_ok "SSH reachable"
}

# ── Template rendering ─────────────────────────────────────────────────────
# render_template <template> <output>
# Substitutes the instance knobs into a deploy/ template. Tokens are __NAME__
# (never $NAME) because nginx templates legitimately contain $host/$uri/$scheme,
# which envsubst would clobber. Fails if any token is left unreplaced.
render_template() {
  local src=$1 dst=$2
  [ -f "$src" ] || die "render_template: $src missing"
  sed -e "s#__APP_ROOT__#${APP_ROOT:?APP_ROOT unset}#g" \
      -e "s#__APP_USER__#${APP_USER:?APP_USER unset}#g" \
      -e "s#__APP_PORT__#${APP_PORT:?APP_PORT unset}#g" \
      -e "s#__SERVICE_NAME__#${SERVICE_NAME:?SERVICE_NAME unset}#g" \
      -e "s#__URL_PREFIX__#${URL_PREFIX-}#g" \
      "$src" > "$dst"
  if grep -q '__[A-Z_]*__' "$dst"; then
    die "render_template: unreplaced placeholder(s) in $dst: $(grep -o '__[A-Z_]*__' "$dst" | sort -u | tr '\n' ' ')"
  fi
}

# ── Layout sanity (shared by lib.sh and provision.sh) ──────────────────────
validate_layout() {
  [[ -z "${URL_PREFIX-}" || "$URL_PREFIX" =~ ^/[a-z0-9-]+$ ]] \
    || die "URL_PREFIX must be empty or like /kisschool — no trailing slash (got '${URL_PREFIX-}')"
  [[ "${BASE_URL:-}" =~ ^https?://[^/]+$ ]] \
    || die "BASE_URL must be scheme://host with no path or trailing slash (got '${BASE_URL:-}')"
}
