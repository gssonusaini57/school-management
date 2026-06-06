---
name: Android teacher app shipped
description: KIS school-management has a native Android attendance app for teachers — Kotlin/Compose, signed, distributed via website link.
type: project
originSessionId: 567c8dd7-f9da-473d-b428-b40fbaf9720d
---
A signed Android APK for teachers (Kotlin + Jetpack Compose, ~3 MB, signed v2/v3, minSdk 26 / targetSdk 34). Source in `/Users/manjeetsaini/Documents/GitHub/school-management/android/`. Class scope enforced server-side via the JWT's `allowed_classes`.

**Session 16 rebrand:** package renamed `com.expressonly.kisattendance` → **`in.kisschool`** (backtick-escape the `in` keyword in every package/import). Now ships TWO product flavors via `BuildConfig.API_BASE_URL`: **prod** (`in.kisschool`, → `https://kisschool.in/api/`, published at `kisschool.in/downloads/kis-attendance.apk`) and **staging** (`in.kisschool.test`, → `https://expressonly.in/school/api/`, published at `expressonly.in/school/downloads/kis-attendance.apk`). `.test` suffix lets both install side-by-side. Build: `bash scripts/build-android.sh {prod|test}`. Because the package changed, phones with the OLD `com.expressonly…` app must install fresh (new app identity). Pitfall: the R8 keep rule must track the package name — see [[feedback_android_r8_package_rename]].

**Screens (Session 16 additions):** Login redesigned to match web (gradient/crest/remember-me + Forgot-password link); **Edit Student** (full validation, staff edits queue as edit-requests) + **document upload/preview** (Coil; photo/dob_cert/aadhar via multipart `POST /students/{id}/documents/{kind}`); **Marks Entry** (draft→submit→lock→request-edit). `/students` is paginated → client reads `.items`.

**Build & ship pipeline (Session 6 + follow-up):**
- `/release-android` (slash command) is the single end-to-end entry point. It runs `bash scripts/build-android.sh`, asks `y/N`, then runs `bash scripts/deploy/test/upload-apk.sh` which rsyncs **only the APK file** (no SPA rebuild — the web download link `/school/downloads/kis-attendance.apk` is stable and was deployed once in Session 6).
- For build-only (no upload): `bash scripts/build-android.sh`.
- `/deploy-test-frontend` is still the right command if the SPA itself changed — it ships `frontend/dist/` (which includes the latest APK from `public/downloads/`) end-to-end.

**Versioning:** `android/version.properties` is the single source of truth (`versionCode=N`, `versionName=X.Y.Z`); `app/build.gradle.kts` reads it at configure time. `scripts/build-android.sh` auto-increments `versionCode` on every release build (commits the new value back to the file). `versionName` stays manual — edit `version.properties` directly when you want a user-visible bump. In-app, the version is shown in two places (both read `BuildConfig`): a small footer "v{name} · build {code}" under the Sign-in button on Login, and an "About" dropdown menu item on Home that opens an AlertDialog with full info.

**Why:** Teachers wanted a phone-native flow ("open app → mark attendance") faster than loading the web in mobile Chrome. Plan was approved 2026-05-08; shipped same session.

**How to apply:** When the user mentions "the teacher app", "the Android app", "the APK", or attendance UX on phones, this is the artifact. For new screens / features, follow the existing `screens/{name}/{Name}Screen.kt + {Name}ViewModel.kt` pattern and add the route to `ui/nav/AppNav.kt`. To ship a new version: just run `/release-android` — versionCode auto-bumps. To ship a new user-visible version (e.g. 1.0.0 → 1.1.0), edit `android/version.properties` first, then `/release-android`. The release keystore at `android/keystore/kis-release.jks` is irreplaceable — every update for the lifetime of the app must be signed with it. Password lives in `android/keystore/keystore.properties` (gitignored). Both files MUST be backed up outside the repo.
