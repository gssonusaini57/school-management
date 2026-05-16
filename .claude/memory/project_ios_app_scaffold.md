---
name: iOS app scaffolded
description: SwiftUI iOS teacher app exists at ios/, mirrors android/. Distribution blocked by Apple Dev account requirement.
type: project
originSessionId: 097ff711-dee0-4cce-82a9-6bee588b3ae0
---
iOS app scaffolded in `ios/` (Session 7, 2026-05-08). SwiftUI + URLSession + Keychain, no third-party deps. Mirrors `android/` 1:1 (6 screens, same JWT/access-code login, same backend).

XcodeGen-driven: `ios/project.yml` is source of truth, `.xcodeproj` is gitignored. Build via `brew install xcodegen && cd ios && xcodegen && open KisAttendance.xcodeproj` or `./scripts/build-ios.sh` for an .ipa.

**Why:** User asked for parity with the Android app so iPhone-using teachers aren't excluded.

**How to apply:** When user wants to add a feature to "the mobile app", confirm whether it's Android-only, iOS-only, or both — iOS files in `ios/KisAttendance/UI/` parallel the Kotlin files in `android/.../ui/screens/`. When user wants to ship iOS, the gating step is an Apple Developer Program membership ($99/yr) — there's no APK-style sideload on iOS. The web `/mobile-apps` page accurately shows iOS as "Coming soon — TestFlight invite required" until then.
