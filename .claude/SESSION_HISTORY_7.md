# Session 7 — 2026-05-08 (later) · iOS app scaffold + Mobile Apps page

**Focus:** Add an iOS native app parallel to `android/`, move the APK link off Login into a dedicated post-login menu page that lists both apps.

**Web changes:**
- Removed the "Download for Android" footer block from [Login.tsx](../frontend/src/pages/Login.tsx) — login is now form-only.
- New [MobileApps.tsx](../frontend/src/pages/MobileApps.tsx) at `/mobile-apps`. Two cards (Android = Available + direct APK download; iOS = Coming soon + TestFlight steps). Both list install instructions in a muted box.
- Sidebar got a new "Resources" section with a single `Smartphone`-iconed entry. Available to all roles (admin + staff). Links: [Layout.tsx](../frontend/src/components/Layout.tsx) + [App.tsx](../frontend/src/App.tsx).

**iOS app — `ios/` (new top-level project, mirrors `android/` philosophy):**
- Stack: SwiftUI + URLSession + async/await + Keychain (no third-party deps; no CocoaPods/SPM dependencies). iOS 16+, SwiftUI `NavigationStack`. Bundle id `in.expressonly.kisattendance`.
- **XcodeGen-driven:** `ios/project.yml` is the single source of truth — the `.xcodeproj` is gitignored and regenerated via `brew install xcodegen && xcodegen`. Treat it like Android's `build.gradle.kts`. Reasoning: `.pbxproj` is a UUID-laden monstrosity that nobody enjoys merging.
- Same 6 screens as Android, file-for-file: [LoginView](../ios/KisAttendance/UI/Login/LoginView.swift) (admin segmented control + staff access code), [HomeView](../ios/KisAttendance/UI/Home/HomeView.swift) (3 tiles + ⋯ menu with About + Logout), [TakeAttendanceView](../ios/KisAttendance/UI/Attendance/TakeAttendanceView.swift) (P/A/L chips, defaults to Present, save), [HistoryView](../ios/KisAttendance/UI/History/HistoryView.swift) (read-only), [StudentsListView](../ios/KisAttendance/UI/Students/StudentsListView.swift) + [StudentDetailView](../ios/KisAttendance/UI/Students/StudentDetailView.swift). Class scope read from JWT `allowed_classes`.
- [ApiClient](../ios/KisAttendance/Data/ApiClient.swift) is a singleton URLSession wrapper that mounts everything under `https://expressonly.in/school/api/`, attaches `Bearer <jwt>`, and on 401 posts `kis.authExpired` Notification → `AppRoot.onReceive` calls `session.logout()` (parallel to Android's `authExpired` SharedFlow).
- [AuthStore](../ios/KisAttendance/Data/AuthStore.swift) persists token + name + classes in Keychain (`kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`) — iOS analogue of Android's EncryptedSharedPreferences.
- Versioning mirrors Android: [version.xcconfig](../ios/version.xcconfig) holds `MARKETING_VERSION` + `CURRENT_PROJECT_VERSION`; [scripts/build-ios.sh](../ios/scripts/build-ios.sh) auto-increments the build number, runs xcodegen, archives Release, exports `.ipa` (development signing). `--no-bump` flag for rebuilds.
- README at [ios/README.md](../ios/README.md) covers setup, distribution paths (TestFlight/Ad Hoc/App Store), and arch parallels with Android.

**Distribution reality (documented for future):**
- iOS has no APK-style sideload — every install path requires Apple infrastructure ($99/yr Apple Dev Program). The Mobile Apps page accurately marks iOS as "Coming soon — TestFlight invite required" until that's set up. The build script's export plist sets `method=development`; flip it to `app-store` + use `xcrun altool` once the user has App Store Connect.
- Code signing not configured in repo — relies on Xcode's Automatic signing reading the user's signed-in Apple ID. Nothing to back up at this stage; once a distribution cert is created (Apple Dev portal), it joins the irreplaceable list alongside the Android keystore.

**Outcome:**
- Frontend type-checks clean (`tsc --noEmit` passes).
- ✅ **Deployed to TEST** via `/deploy-test-all` at 08:01 IST. Snapshot retained: `app_20260508_080042.tgz` + `db_20260508_080042.sql.gz`. Live URLs verified (SPA, `/api/health`, APK download all 200). Bundle: 745 KB JS / 235 KB gz (≈+1 KB gz).
- iOS build NOT verified — this Mac has only Command Line Tools, not full Xcode. `xcodegen` not installed either. User chose to defer iOS build (would need ~10 GB Xcode install from App Store + `brew install xcodegen`).
- ⚠️ Pending user actions: (a) install Xcode + run `cd ios && xcodegen && open KisAttendance.xcodeproj` to verify iOS source compiles, (b) decide on Apple Dev account ($99/yr) before iOS can reach phones — until then the `/mobile-apps` page accurately marks iOS as "Coming soon — TestFlight invite required".
