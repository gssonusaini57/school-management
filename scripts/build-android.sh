#!/usr/bin/env bash
# Build the signed release Android APK and copy it into frontend/public/downloads/
# so the next frontend deploy publishes it to https://expressonly.in/school/downloads/kis-attendance.apk

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ANDROID_DIR="$REPO_ROOT/android"
DOWNLOAD_DIR="$REPO_ROOT/frontend/public/downloads"
TARGET_APK="$DOWNLOAD_DIR/kis-attendance.apk"

if [[ ! -f "$ANDROID_DIR/keystore/keystore.properties" ]]; then
    echo "ERROR: $ANDROID_DIR/keystore/keystore.properties not found." >&2
    echo "       Run the keystore setup steps in android/README.md first." >&2
    exit 1
fi

# Auto-bump versionCode so every release APK has a unique, monotonic build number.
# versionName stays manual — edit android/version.properties when you want a
# user-visible version bump (e.g. 1.0.0 → 1.1.0).
VERSION_FILE="$ANDROID_DIR/version.properties"
if [[ -f "$VERSION_FILE" ]]; then
    OLD_VC=$(grep -E '^versionCode=' "$VERSION_FILE" | cut -d= -f2)
    NEW_VC=$((OLD_VC + 1))
    VN=$(grep -E '^versionName=' "$VERSION_FILE" | cut -d= -f2)
    # Use a portable in-place sed (works on macOS + Linux)
    sed -i.bak "s/^versionCode=.*/versionCode=$NEW_VC/" "$VERSION_FILE" && rm -f "$VERSION_FILE.bak"
    echo "==> Version bump: ${VN} build ${OLD_VC} → ${VN} build ${NEW_VC}"
else
    echo "WARN: $VERSION_FILE missing — using whatever's in build.gradle.kts" >&2
fi

cd "$ANDROID_DIR"

echo "==> Building release APK…"
./gradlew --no-daemon :app:assembleRelease

BUILT_APK="app/build/outputs/apk/release/app-release.apk"
if [[ ! -f "$BUILT_APK" ]]; then
    echo "ERROR: expected APK not produced at $ANDROID_DIR/$BUILT_APK" >&2
    exit 1
fi

mkdir -p "$DOWNLOAD_DIR"
cp -f "$BUILT_APK" "$TARGET_APK"

SIZE=$(du -h "$TARGET_APK" | awk '{print $1}')
echo
echo "✓ APK ready ($SIZE) at:"
echo "    $TARGET_APK"
echo
echo "Next step: bash scripts/deploy/test/deploy-frontend.sh"
echo "  → publishes to https://expressonly.in/school/downloads/kis-attendance.apk"
