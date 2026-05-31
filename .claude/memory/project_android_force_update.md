---
name: project_android_force_update
description: Android force-update gate — app polls app-version.json on launch and blocks old builds; every release auto-bumps version.
metadata: 
  node_type: memory
  type: project
  originSessionId: df87bf8a-36fb-4e09-9510-12bbdd0d215e
---

Session 14 (2026-05-31). The Android teacher app has a **force-update gate**: on launch it fetches a version manifest and shows a non-dismissable "Update required" `Dialog` if its `versionCode` is below `min_version_code`.

- Manifest: `https://kisschool.in/downloads/app-version.json` (prod) / `…/school/downloads/app-version-test.json` (test). Per-flavor URL is `BuildConfig.APP_VERSION_URL`.
- Code: `android/.../ui/update/UpdateGate.kt` (wraps AppNav in MainActivity), `data/repo/AppUpdateRepository.kt`, DTO `AppVersionDto`, `ApiService.appVersion(@Url)`.
- **Fails open**: any fetch/parse error → app stays usable (never lock teachers out on a network blip).
- `scripts/build-android.sh` writes the manifest with `min = latest = <this build>` → **every release forces all older GATED installs to update**. To ship an OPTIONAL update, hand-lower `min_version_code` below `latest` in the published JSON.
- **First-gate caveat:** the gate ships starting v1.2.1 (build 14). Pre-gate installs (≤build 13) have no gate code, so they are NOT auto-forced — teachers must update once manually. From build 15+ the force works automatically.
- `build-android.sh` now auto-bumps BOTH `versionCode +1` AND `versionName` patch (e.g. 1.2.0→1.2.1) every build (was versionCode-only — supersedes Gotcha #7's "versionName stays manual"). Edit version.properties by hand only for a major/minor feature bump.
- `upload-apk.sh` (prod+test) verifies the APK serves HTTP 200 BEFORE publishing the manifest, so a failed APK upload can't arm the gate behind a dead download link. See [[project_android_teacher_app]].
