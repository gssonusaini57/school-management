#!/usr/bin/env bash
# Build the iOS app from CI-friendly text config and produce an .ipa.
#
# Requirements:
#   - Xcode 15+ installed (`xcode-select -p` must point at a Developer dir)
#   - XcodeGen on PATH (`brew install xcodegen`)
#   - An Apple Developer team configured in Xcode (Sign in via Xcode → Settings → Accounts)
#
# Usage:
#   ./ios/scripts/build-ios.sh                       # auto-bumps build number, builds Release archive + .ipa
#   ./ios/scripts/build-ios.sh --no-bump             # skip build number increment (rebuild same version)
#
# Output:
#   ios/build/KisAttendance.ipa
#   ios/build/KisAttendance.xcarchive

set -euo pipefail

cd "$(dirname "$0")/.."  # land in ios/

BUMP=1
for arg in "$@"; do
  [ "$arg" = "--no-bump" ] && BUMP=0
done

# 1) Ensure XcodeGen is installed
if ! command -v xcodegen >/dev/null 2>&1; then
  echo "✗ xcodegen not found. Install with: brew install xcodegen"
  exit 1
fi

# 2) Auto-increment build number unless told not to
if [ "$BUMP" = "1" ]; then
  current=$(grep -E '^CURRENT_PROJECT_VERSION' version.xcconfig | awk -F'=' '{ print $2 }' | tr -d ' ')
  next=$((current + 1))
  sed -i.bak "s/^CURRENT_PROJECT_VERSION = .*/CURRENT_PROJECT_VERSION = $next/" version.xcconfig
  rm -f version.xcconfig.bak
  echo "→ Bumped CURRENT_PROJECT_VERSION: $current → $next"
fi

# 3) Generate the .xcodeproj
echo "→ Running xcodegen…"
xcodegen --quiet

# 4) Archive (Release)
mkdir -p build
ARCHIVE=build/KisAttendance.xcarchive
echo "→ Archiving…"
xcodebuild \
  -project KisAttendance.xcodeproj \
  -scheme KisAttendance \
  -configuration Release \
  -destination "generic/platform=iOS" \
  -archivePath "$ARCHIVE" \
  archive | xcpretty || true

# 5) Export .ipa
EXPORT_OPTS=$(mktemp)
cat > "$EXPORT_OPTS" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>method</key>
  <string>development</string>
  <key>signingStyle</key>
  <string>automatic</string>
  <key>compileBitcode</key>
  <false/>
  <key>stripSwiftSymbols</key>
  <true/>
</dict>
</plist>
EOF

echo "→ Exporting .ipa…"
xcodebuild \
  -exportArchive \
  -archivePath "$ARCHIVE" \
  -exportOptionsPlist "$EXPORT_OPTS" \
  -exportPath build | xcpretty || true

rm -f "$EXPORT_OPTS"

if [ -f build/KisAttendance.ipa ]; then
  echo "✓ Built: $(pwd)/build/KisAttendance.ipa"
else
  echo "✗ .ipa was not produced — check the xcodebuild output above (likely a code-signing issue)."
  exit 1
fi
