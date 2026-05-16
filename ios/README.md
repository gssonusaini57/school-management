# KIS Attendance — iOS

Native SwiftUI app that mirrors the Android teacher app (`android/`). Same six screens, same backend (`https://expressonly.in/school/api/`), same access-code login.

## Project layout

```
ios/
├── project.yml                        XcodeGen config — single source of truth
├── version.xcconfig                   MARKETING_VERSION + CURRENT_PROJECT_VERSION
├── KisAttendance/
│   ├── App/KisAttendanceApp.swift     @main entry
│   ├── Data/                          ApiClient · AuthStore (Keychain) · Models
│   ├── UI/
│   │   ├── AppRoot.swift              Login ↔ Home router; observes 401 → logout
│   │   ├── Login/LoginView.swift
│   │   ├── Home/HomeView.swift
│   │   ├── Attendance/TakeAttendanceView.swift
│   │   ├── History/HistoryView.swift
│   │   └── Students/                  StudentsListView · StudentDetailView
│   └── Resources/                     Info.plist · Assets.xcassets
├── scripts/build-ios.sh               Bumps build #, runs xcodegen, archives, exports .ipa
└── .gitignore                         (xcodeproj, build/, DerivedData are not committed)
```

The `.xcodeproj` is **not committed** — it's regenerated from `project.yml`. Treat `project.yml` like Android's `build.gradle.kts`.

## One-time setup

```bash
brew install xcodegen
xcode-select --install      # Command Line Tools (if you haven't already)
```

You also need to be signed into your Apple ID inside **Xcode → Settings → Accounts**, which is what makes Automatic code signing work for both simulator runs and device archives.

## Open in Xcode

```bash
cd ios
xcodegen
open KisAttendance.xcodeproj
```

Pick a simulator → ⌘R. The app talks to live `expressonly.in/school/api/` — sign in with your real staff access code.

## Build a signed .ipa

```bash
cd ios
./scripts/build-ios.sh
# → ios/build/KisAttendance.ipa
```

The script (a) auto-increments `CURRENT_PROJECT_VERSION` in `version.xcconfig`, (b) regenerates the project, (c) archives Release, (d) exports an `.ipa` using **development** signing. Use `--no-bump` to rebuild the same build number.

For TestFlight you'd swap the `<key>method</key>` in `scripts/build-ios.sh` from `development` to `app-store` and `xcrun altool --upload-app …` to App Store Connect — but that requires a paid Apple Developer Program membership ($99/year).

## Distribution paths (all require an Apple Developer account)

| Path | Cost | Notes |
|---|---|---|
| **TestFlight** | $99/yr | Easiest internal distribution. Builds expire after 90 days. Up to 10,000 testers. |
| **Ad Hoc** | $99/yr | Sideload via UDID list (cap 100/yr). Re-sign yearly. |
| **App Store** | $99/yr | Public listing + 1–2 week review. Awkward for a single-school app. |

There's no equivalent of Android's APK sideloading — every install path on iOS goes through Apple infrastructure.

## Versioning

`version.xcconfig` is the single source of truth, mirroring Android's `version.properties`:

```
MARKETING_VERSION = 1.0.0          # user-visible (edit by hand for X.Y.Z bumps)
CURRENT_PROJECT_VERSION = 1        # auto-incremented by build-ios.sh
```

Both values are referenced by `project.yml` → exposed in `Info.plist` → readable as `Bundle.main.infoDictionary["CFBundleShortVersionString" / "CFBundleVersion"]`. The Login footer and Home → About sheet display them.

## Architecture parallels with Android

| Concern | Android | iOS |
|---|---|---|
| HTTP | Retrofit + OkHttp | URLSession + async/await |
| JSON | Gson | Codable |
| Token storage | EncryptedSharedPreferences | Keychain (`AuthStore`) |
| Nav | Compose Navigation | SwiftUI `NavigationStack` |
| 401 handling | OkHttp interceptor → `authExpired` SharedFlow | `ApiClient` posts `kis.authExpired` Notification |
| DI | Manual (`AppContainer`) | Singletons (`ApiClient.shared`, `AuthStore.shared`) |

## Backup + signing

Once you ship via TestFlight or App Store, the **App Store Connect API key** + **distribution certificate** become irreplaceable in the same way the Android keystore is — back them up. (The dev build script uses Xcode's Automatic signing, so nothing to back up until you go to TestFlight.)
