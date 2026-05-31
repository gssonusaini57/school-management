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
MANIFEST_LOCAL="$REPO_ROOT/frontend/public/downloads/app-version-test.json"
APK_REMOTE_DIR="/opt/school-management/frontend/dist/downloads"
APK_REMOTE="$APK_REMOTE_DIR/kis-attendance.apk"
MANIFEST_REMOTE="$APK_REMOTE_DIR/app-version-test.json"

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

# CRITICAL: verify the APK serves before publishing the force-update manifest —
# the manifest gates old installs behind an "Update required" dialog whose only
# action downloads this APK. A dead link would lock teachers out. Abort if the
# APK isn't HTTP 200, leaving the (old) manifest untouched.
APK_URL="https://${DOMAIN}/school/downloads/kis-attendance.apk"
echo "==> Verifying APK is downloadable: $APK_URL"
APK_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$APK_URL" || echo 000)
if [[ "$APK_CODE" != "200" ]]; then
    echo "ERROR: APK not reachable (HTTP $APK_CODE). NOT publishing the version manifest." >&2
    exit 1
fi
echo "✓ APK reachable (HTTP 200)"

# Now safe to publish the force-update manifest alongside the APK (staging variant).
if [[ -f "$MANIFEST_LOCAL" ]]; then
    echo "==> Uploading version manifest → ${MANIFEST_REMOTE}"
    rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
        "$MANIFEST_LOCAL" \
        "${SSH_USER}@${SERVER}:${MANIFEST_REMOTE}"
    ssh -i "$SSH_KEY" "${SSH_USER}@${SERVER}" \
        "chown school:school $MANIFEST_REMOTE && chmod 644 $MANIFEST_REMOTE"
    if ! curl -s "https://${DOMAIN}/school/downloads/app-version-test.json" | grep -q 'latest_version_code'; then
        echo "ERROR: manifest not reachable/valid after upload." >&2
        exit 1
    fi
    echo "✓ Manifest published + verified"
else
    echo "WARN: $MANIFEST_LOCAL missing — force-update manifest NOT updated." >&2
fi

echo
echo "✓ APK live at: $APK_URL"
