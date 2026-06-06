---
name: feedback_android_r8_package_rename
description: Android ProGuard/R8 keep rules must track the package name or release-build Gson (de)serialization silently breaks
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ef13f4d1-04c7-4142-92f5-05bda9964d1f
---

When renaming the Android package (Session 16: `com.expressonly.kisattendance` → `in.kisschool`), the ProGuard keep rule in `android/app/proguard-rules.pro` still pointed at the OLD package, so it matched nothing and **R8 obfuscated every Gson DTO field name in the release build only**. The app then sent login as `{"<garbled>":…}` → backend returned **HTTP 422** ("field required"), and every API call was broken. Debug builds (no minify) hid it completely.

**Why:** Gson maps JSON keys to Kotlin field names by reflection. R8 renames fields unless a keep rule preserves them. The DTOs have no `@SerializedName` on some fields (e.g. `identifier`, `password`, `token`), so their JSON key == field name == must not be obfuscated.

**How to apply:**
- Keep DTOs by their CURRENT package: `-keep class in.kisschool.data.api.dto.** { *; }`.
- Add a safety net: `-keepclassmembers,allowobfuscation class * { @com.google.gson.annotations.SerializedName <fields>; }`.
- After any package rename, grep `proguard-rules.pro` for the old package and update it.
- **Verify** via `android/app/build/outputs/mapping/<flavor>Release/mapping.txt`: the DTO class should map to itself (e.g. `…dto.LoginRequest -> …dto.LoginRequest`), not to an obfuscated name. Always smoke-test login on a real RELEASE build, not just debug.

Related rename gotchas: `in` is a Kotlin hard keyword → backtick-escape it in every `package`/`import` (`` `in`.kisschool ``); Gradle `namespace`/`applicationId` strings don't need backticks. AGP forbids a product-flavor name starting with `test` → the staging flavor is named `staging` with `applicationIdSuffix = ".test"`. See [[project_android_teacher_app]].
