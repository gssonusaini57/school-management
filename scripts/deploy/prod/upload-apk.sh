#!/usr/bin/env bash
# Upload ONLY the freshly-built PROD Android APK to the prod server.
# Skips the npm/Vite rebuild — only the APK file changes between releases.
#
# PROD serves the *prod* flavour (applicationId in.kisschool, API
# https://kisschool.in/api/) at the stable filename kis-attendance.apk.
#
# Pre-condition: scripts/build-android.sh prod has produced
#   frontend/public/downloads/kis-attendance.apk  (+ app-version.json)

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh"
# shellcheck disable=SC1091
source "$HERE/../common/lib.sh"

APK_LOCAL="$REPO_ROOT/frontend/public/downloads/$APK_LOCAL_NAME"
MANIFEST_LOCAL="$REPO_ROOT/frontend/public/downloads/$MANIFEST_NAME"
APK_REMOTE_DIR="$APP_ROOT/frontend/dist/downloads"
APK_REMOTE="$APK_REMOTE_DIR/kis-attendance.apk"
MANIFEST_REMOTE="$APK_REMOTE_DIR/$MANIFEST_NAME"
APK_URL="${DOWNLOADS_URL}/kis-attendance.apk"
MANIFEST_URL="${DOWNLOADS_URL}/${MANIFEST_NAME}"

if [[ ! -f "$APK_LOCAL" ]]; then
    echo "ERROR: APK not found at $APK_LOCAL" >&2
    echo "       Run 'bash scripts/build-android.sh $ENV' first." >&2
    exit 1
fi

SIZE=$(du -h "$APK_LOCAL" | awk '{print $1}')
echo "==> Uploading PROD APK ($SIZE) → ${SSH_USER}@${SERVER}:${APK_REMOTE}"

ssh_run "mkdir -p $APK_REMOTE_DIR" </dev/null
scp_up --progress "$APK_LOCAL" "${SSH_USER}@${SERVER}:${APK_REMOTE}"
ssh_run "chown $APP_USER:$APP_USER $APK_REMOTE && chmod 644 $APK_REMOTE" </dev/null

# CRITICAL: verify the APK is actually downloadable BEFORE publishing the
# force-update manifest. The manifest arms a non-dismissable "Update required"
# dialog whose only action is downloading this APK — if the file is unreachable,
# every gated install is locked out behind a dead link. So if the APK doesn't
# serve HTTP 200 with the right size, abort WITHOUT touching the manifest.
echo "==> Verifying APK is downloadable: $APK_URL"
APK_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$APK_URL" || echo 000)
if [[ "$APK_CODE" != "200" ]]; then
    echo "ERROR: APK not reachable (HTTP $APK_CODE). NOT publishing the version manifest." >&2
    exit 1
fi
LOCAL_BYTES=$(wc -c < "$APK_LOCAL" | tr -d ' ')
REMOTE_BYTES=$(curl -sI "$APK_URL" | awk 'tolower($1)=="content-length:"{print $2}' | tr -d '\r')
if [[ "$REMOTE_BYTES" != "$LOCAL_BYTES" ]]; then
    echo "ERROR: served APK is $REMOTE_BYTES bytes, local is $LOCAL_BYTES. NOT publishing the manifest." >&2
    exit 1
fi
echo "✓ APK reachable (HTTP 200, $LOCAL_BYTES bytes)"

# Now safe to publish the force-update manifest alongside the APK.
if [[ -f "$MANIFEST_LOCAL" ]]; then
    echo "==> Uploading version manifest → ${MANIFEST_REMOTE}"
    scp_up "$MANIFEST_LOCAL" "${SSH_USER}@${SERVER}:${MANIFEST_REMOTE}"
    ssh_run "chown $APP_USER:$APP_USER $MANIFEST_REMOTE && chmod 644 $MANIFEST_REMOTE" </dev/null
    if ! curl -s "$MANIFEST_URL" | grep -q 'latest_version_code'; then
        echo "ERROR: manifest not reachable/valid after upload: $MANIFEST_URL" >&2
        exit 1
    fi
    echo "✓ Manifest published + verified"
else
    echo "WARN: $MANIFEST_LOCAL missing — force-update manifest NOT updated." >&2
fi

echo
echo "✓ APK live at: $APK_URL"
echo
echo "Manifest ($MANIFEST_URL):"
curl -s "$MANIFEST_URL" | head -10
