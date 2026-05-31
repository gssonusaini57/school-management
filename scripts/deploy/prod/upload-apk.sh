#!/usr/bin/env bash
# Upload ONLY the freshly-built PROD Android APK to the prod server.
# Skips the npm/Vite rebuild — only the APK file changes between releases.
#
# PROD serves the *prod* flavor (applicationId in.kisschool, API
# https://kisschool.in/api/) at the stable filename kis-attendance.apk.
#
# Pre-condition: scripts/build-android.sh prod has produced
#   frontend/public/downloads/kis-attendance.apk

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"

APK_LOCAL="$REPO_ROOT/frontend/public/downloads/kis-attendance.apk"
MANIFEST_LOCAL="$REPO_ROOT/frontend/public/downloads/app-version.json"
APK_REMOTE_DIR="/opt/school-management/frontend/dist/downloads"
APK_REMOTE="$APK_REMOTE_DIR/kis-attendance.apk"
MANIFEST_REMOTE="$APK_REMOTE_DIR/app-version.json"

if [[ ! -f "$APK_LOCAL" ]]; then
    echo "ERROR: prod APK not found at $APK_LOCAL" >&2
    echo "       Run 'bash scripts/build-android.sh prod' first." >&2
    exit 1
fi

SIZE=$(du -h "$APK_LOCAL" | awk '{print $1}')
echo "==> Uploading PROD APK ($SIZE) → ${SSH_USER}@${SERVER}:${APK_REMOTE}"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "${SSH_USER}@${SERVER}" \
    "mkdir -p $APK_REMOTE_DIR"

rsync -az --progress -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
    "$APK_LOCAL" \
    "${SSH_USER}@${SERVER}:${APK_REMOTE}"

ssh -i "$SSH_KEY" "${SSH_USER}@${SERVER}" \
    "chown school:school $APK_REMOTE && chmod 644 $APK_REMOTE"

# CRITICAL: verify the APK is actually downloadable BEFORE publishing the
# force-update manifest. The manifest arms a non-dismissable "Update required"
# dialog whose only action is downloading this APK — if the file is unreachable,
# every gated teacher is permanently locked out behind a dead link. So if the
# APK doesn't serve HTTP 200, abort WITHOUT touching the manifest.
APK_URL="https://${DOMAIN}/downloads/kis-attendance.apk"
echo "==> Verifying APK is downloadable: $APK_URL"
APK_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$APK_URL" || echo 000)
if [[ "$APK_CODE" != "200" ]]; then
    echo "ERROR: APK not reachable (HTTP $APK_CODE). NOT publishing the version manifest" >&2
    echo "       to avoid locking out teachers behind a dead download link." >&2
    exit 1
fi
echo "✓ APK reachable (HTTP 200)"

# Now safe to publish the force-update manifest alongside the APK.
if [[ -f "$MANIFEST_LOCAL" ]]; then
    echo "==> Uploading version manifest → ${MANIFEST_REMOTE}"
    rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
        "$MANIFEST_LOCAL" \
        "${SSH_USER}@${SERVER}:${MANIFEST_REMOTE}"
    ssh -i "$SSH_KEY" "${SSH_USER}@${SERVER}" \
        "chown school:school $MANIFEST_REMOTE && chmod 644 $MANIFEST_REMOTE"
    if ! curl -s "https://${DOMAIN}/downloads/app-version.json" | grep -q 'latest_version_code'; then
        echo "ERROR: manifest not reachable/valid after upload." >&2
        exit 1
    fi
    echo "✓ Manifest published + verified"
else
    echo "WARN: $MANIFEST_LOCAL missing — force-update manifest NOT updated." >&2
fi

echo
echo "✓ APK live at: $APK_URL"
echo
echo "Manifest:"
curl -s "https://${DOMAIN}/downloads/app-version.json" | head -10
