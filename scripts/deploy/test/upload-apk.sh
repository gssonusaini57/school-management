#!/usr/bin/env bash
# Upload ONLY the freshly-built Android APK to the TEST server.
# Skips the npm/Vite rebuild — the SPA + download link are already deployed;
# only the APK file changes between releases.
#
# TEST serves the *staging* flavor (applicationId in.kisschool.test, API
# https://expressonly.in/school/api/) but publishes it under the stable filename
# kis-attendance.apk so the existing /school/downloads link keeps working.
#
# Pre-condition: scripts/build-android.sh test has produced
#   frontend/public/downloads/kis-attendance-test.apk

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"

APK_LOCAL="$REPO_ROOT/frontend/public/downloads/kis-attendance-test.apk"
APK_REMOTE_DIR="/opt/school-management/frontend/dist/downloads"
APK_REMOTE="$APK_REMOTE_DIR/kis-attendance.apk"

if [[ ! -f "$APK_LOCAL" ]]; then
    echo "ERROR: staging APK not found at $APK_LOCAL" >&2
    echo "       Run 'bash scripts/build-android.sh test' first." >&2
    exit 1
fi

SIZE=$(du -h "$APK_LOCAL" | awk '{print $1}')
echo "==> Uploading APK ($SIZE) → ${SSH_USER}@${SERVER}:${APK_REMOTE}"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SERVER}" \
    "mkdir -p $APK_REMOTE_DIR"

rsync -az --progress -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
    "$APK_LOCAL" \
    "${SSH_USER}@${SERVER}:${APK_REMOTE}"

ssh -i "$SSH_KEY" "${SSH_USER}@${SERVER}" \
    "chown school:school $APK_REMOTE && chmod 644 $APK_REMOTE"

echo
echo "✓ APK live at: https://${DOMAIN}/school/downloads/kis-attendance.apk"
echo
echo "Verifying…"
curl -sI "https://${DOMAIN}/school/downloads/kis-attendance.apk" | head -5
