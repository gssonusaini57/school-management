#!/usr/bin/env bash
# Build a signed release Android APK for the chosen flavor and copy it into
# frontend/public/downloads/ so the next frontend deploy publishes it.
#
# Usage:
#   bash scripts/build-android.sh          # prod  → kis-attendance.apk      (talks to kisschool.in)
#   bash scripts/build-android.sh test     # test  → kis-attendance-test.apk (talks to expressonly.in/school)
#
# Flavors are defined in android/app/build.gradle.kts:
#   prod → applicationId in.kisschool,      API https://kisschool.in/api/
#   test → applicationId in.kisschool.test, API https://expressonly.in/school/api/
# The .test suffix lets both APKs be installed on the same phone at once.

set -euo pipefail

FLAVOR="${1:-prod}"
case "$FLAVOR" in
    prod) APK_NAME="kis-attendance.apk";      GRADLE_TASK=":app:assembleProdRelease"; OUT_DIR="prod/release";  OUT_APK="app-prod-release.apk" ;;
    test) APK_NAME="kis-attendance-test.apk"; GRADLE_TASK=":app:assembleStagingRelease"; OUT_DIR="staging/release";  OUT_APK="app-staging-release.apk" ;;
    *) echo "ERROR: unknown flavor '$FLAVOR' (use 'prod' or 'test')" >&2; exit 2 ;;
esac

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ANDROID_DIR="$REPO_ROOT/android"
DOWNLOAD_DIR="$REPO_ROOT/frontend/public/downloads"
TARGET_APK="$DOWNLOAD_DIR/$APK_NAME"

if [[ ! -f "$ANDROID_DIR/keystore/keystore.properties" ]]; then
    echo "ERROR: $ANDROID_DIR/keystore/keystore.properties not found." >&2
    echo "       Run the keystore setup steps in android/README.md first." >&2
    exit 1
fi

# Auto-bump EVERY release so each APK is a new, forceable version:
#   - versionCode +1   → unique monotonic build number (the force-update gate keys on this)
#   - versionName patch +1 (e.g. 1.2.0 → 1.2.1) → a fresh user-visible version too
# For a major/minor feature bump, edit version.properties by hand first (e.g. set
# 1.2.0 → 1.3.0); the patch then auto-increments from there on the next build.
VERSION_FILE="$ANDROID_DIR/version.properties"
if [[ -f "$VERSION_FILE" ]]; then
    OLD_VC=$(grep -E '^versionCode=' "$VERSION_FILE" | cut -d= -f2)
    NEW_VC=$((OLD_VC + 1))
    OLD_VN=$(grep -E '^versionName=' "$VERSION_FILE" | cut -d= -f2)
    IFS='.' read -r VN_MAJ VN_MIN VN_PATCH <<< "$OLD_VN"
    VN_MAJ="${VN_MAJ:-1}"; VN_MIN="${VN_MIN:-0}"; VN_PATCH="${VN_PATCH:-0}"
    VN="${VN_MAJ}.${VN_MIN}.$((VN_PATCH + 1))"
    # Portable in-place sed (works on macOS + Linux)
    sed -i.bak \
        -e "s/^versionCode=.*/versionCode=$NEW_VC/" \
        -e "s/^versionName=.*/versionName=$VN/" \
        "$VERSION_FILE" && rm -f "$VERSION_FILE.bak"
    echo "==> Version bump: ${OLD_VN} (build ${OLD_VC}) → ${VN} (build ${NEW_VC})"
else
    echo "WARN: $VERSION_FILE missing — using whatever's in build.gradle.kts" >&2
fi

cd "$ANDROID_DIR"

echo "==> Building $FLAVOR release APK ($GRADLE_TASK)…"
./gradlew --no-daemon "$GRADLE_TASK"

BUILT_APK="app/build/outputs/apk/$OUT_DIR/$OUT_APK"
if [[ ! -f "$BUILT_APK" ]]; then
    echo "ERROR: expected APK not produced at $ANDROID_DIR/$BUILT_APK" >&2
    exit 1
fi

mkdir -p "$DOWNLOAD_DIR"
cp -f "$BUILT_APK" "$TARGET_APK"

# ── Publish the force-update manifest next to the APK ────────────────────────
# The installed app polls this on launch (downloads/app-version.json). Setting
# min_version_code == this build forces every older (gated) install to update.
# To make a release an *optional* update instead, lower min_version_code by hand
# in the published JSON (or here) so it stays below latest_version_code.
if [[ "$FLAVOR" == "prod" ]]; then
    MANIFEST="$DOWNLOAD_DIR/app-version.json"
    MANIFEST_APK_URL="https://kisschool.in/downloads/kis-attendance.apk"
else
    MANIFEST="$DOWNLOAD_DIR/app-version-test.json"
    # The test box serves the staging APK under the stable kis-attendance.apk name
    # (see scripts/deploy/test/upload-apk.sh), so point the manifest there.
    MANIFEST_APK_URL="https://expressonly.in/school/downloads/kis-attendance.apk"
fi
cat > "$MANIFEST" <<JSON
{
  "latest_version_code": ${NEW_VC:-0},
  "min_version_code": ${NEW_VC:-0},
  "latest_version_name": "${VN:-1.0.0}",
  "apk_url": "$MANIFEST_APK_URL",
  "notes": "Please update to the latest version to continue."
}
JSON
echo "==> Wrote version manifest: $MANIFEST (min = latest = ${NEW_VC:-0})"

SIZE=$(du -h "$TARGET_APK" | awk '{print $1}')
echo
echo "✓ $FLAVOR APK ready ($SIZE) at:"
echo "    $TARGET_APK"
echo
if [[ "$FLAVOR" == "prod" ]]; then
    echo "Next step: bash scripts/deploy/prod/deploy-frontend.sh"
    echo "  → publishes to https://kisschool.in/downloads/kis-attendance.apk"
else
    echo "Test APK built. Sideload it directly, or deploy via the test frontend if you publish it."
fi
