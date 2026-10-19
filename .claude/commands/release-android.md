---
name: release-android
description: Build a signed Android APK for a chosen flavor (prod or test) and, after explicit y/N confirmation, upload just the APK file to its server — prod → kisschool.in/downloads, test → 69.62.72.137/kisschool/downloads. Does NOT rebuild the SPA.
---

# Release Android APK

End-to-end "ship a new APK" command. Builds the signed release APK for the chosen
**flavor**, copies it into `frontend/public/downloads/`, and — only after the user
types `y` — uploads **just the APK file** to that flavor's server.

The app ships in two flavors (defined in `android/app/build.gradle.kts`):

| Flavor | applicationId | API base URL | Local file | Served at |
|---|---|---|---|---|
| **prod** | `in.kisschool` | `https://kisschool.in/api/` | `kis-attendance.apk` | `https://kisschool.in/downloads/kis-attendance.apk` |
| **test** (internal flavor name `staging`) | `in.kisschool.test` | `http://69.62.72.137/kisschool/api/` | `kis-attendance-test.apk` | `http://69.62.72.137/kisschool/downloads/kis-attendance.apk` |

The `.test` applicationId suffix means both can be installed on one phone. The web
"Download for Android" link points at the stable `kis-attendance.apk` filename on
each server, so the SPA never needs redeploying for an APK update.

TEST is plain HTTP, so the staging flavour ships its own
`android/app/src/staging/res/xml/network_security_config.xml` that allows cleartext for
`69.62.72.137` only (prod keeps main's HTTPS-only file). Download URLs and manifest names
come from `scripts/deploy/<env>/env.sh` (`DOWNLOADS_URL`, `MANIFEST_NAME`).

## Step 0 — Ask which flavor

If the user didn't say, ask: **prod** (default, → prod server) or **test** (→ test server)?

## Pre-flight

1. Confirm the keystore + properties exist (same keystore signs both flavors):
   ```bash
   test -f android/keystore/kis-release.jks && \
   test -f android/keystore/keystore.properties \
     || { echo "ERROR: keystore missing — see android/README.md"; exit 1; }
   ```
2. `git status` for `android/` and `frontend/` — warn if dirty (don't block).
3. **Every build auto-bumps the version** in `scripts/build-android.sh`: `versionCode +1`
   **and** the `versionName` patch (e.g. `1.2.0 → 1.2.1`). For a feature release, edit
   `android/version.properties` by hand first to bump the major/minor (e.g. `1.2.x → 1.3.0`);
   the patch auto-increments from there. You don't need to bump anything manually for a
   routine release — just build.

## Force-update gate (every release locks out older installs)

The app polls a published manifest on launch and **force-updates** any build older than it:

| | Path |
|---|---|
| prod manifest | `https://kisschool.in/downloads/app-version.json` |
| test manifest | `http://69.62.72.137/kisschool/downloads/app-version-test.json` |

`scripts/build-android.sh` writes this manifest next to the APK with
`min_version_code == latest_version_code == <this build>`, so **every release forces all
older (gated) installs to update** — a non-dismissable "Update required" screen whose only
action downloads the new APK. The Android side ([ui/update/UpdateGate.kt](../../android/app/src/main/java/in/kisschool/ui/update/UpdateGate.kt))
**fails open**: any fetch/parse error leaves the app usable, so a server hiccup can't lock anyone out.

- **To make a release OPTIONAL** (soft "Update available" prompt the teacher can dismiss):
  after building, hand-edit the published `app-version.json` so `min_version_code` is **below**
  `latest_version_code`, then re-upload it.
- The gate only affects builds that already SHIP the gate (v1.2.x+). Pre-gate installs keep
  working and must be updated manually once.
- The `upload-apk.sh` scripts verify the APK serves **HTTP 200 before** publishing the
  manifest — so a failed APK upload can never arm the gate behind a dead download link.

## Action

### Step 1 — Build the APK for the chosen flavor

```bash
bash scripts/build-android.sh prod    # or: bash scripts/build-android.sh test
```

Runs `:app:assembleProdRelease` (or `:app:assembleStagingRelease`) and copies the
signed APK to `frontend/public/downloads/`. Expect ~3 MB and `BUILD SUCCESSFUL`.

### Step 2 — Show APK summary and ASK for upload confirmation

After the build succeeds, **stop and ask explicitly**, naming the right URL:

> APK built — N.N MB. Upload to **<prod|test>** so it's live at
> `<https://kisschool.in|http://69.62.72.137/kisschool>/downloads/kis-attendance.apk`?
> Type `y` to upload, anything else to skip.

**Do not auto-upload** — every push is a real action against a live server. A
**prod** upload warrants extra care (it's production).

### Step 3 — Upload just the APK (no SPA rebuild)

```bash
# prod flavor →
bash scripts/deploy/prod/upload-apk.sh
# test flavor →
bash scripts/deploy/test/upload-apk.sh
```

Each rsyncs its APK → `<APP_ROOT>/frontend/dist/downloads/kis-attendance.apk` on the same
box 69.62.72.137 (key `~/.ssh/enamfoss_prod`): prod → `/opt/school-management`, test →
`/opt/school-management-test`. It then checks the served APK is HTTP 200 **with the local
byte size** before publishing the manifest, and prints the live manifest.

## After running

- Verify: `curl -sI <DOWNLOADS_URL>/kis-attendance.apk` → `HTTP 200` and
  `Content-Length` matching the local APK (upload-apk.sh already enforces this).
- Reminder: bumping `versionCode`/`versionName` makes it an update; the **same**
  keystore must keep signing. Because the package was renamed to `in.kisschool`
  (from the old `com.expressonly.kisattendance`), phones with the *old* app installed
  must install fresh — it's a new app identity, not an update.

## Failure modes

- **Keystore missing:** stop early, point at `android/README.md`.
- **`assemble…Release` failed:** surface the Gradle error; don't upload.
- **APK built but user said `n`:** APK is staged in `frontend/public/downloads/`; they
  can upload later via the matching `upload-apk.sh`.
- **Upload failed (SSH/rsync):** surface the error; the local APK is intact for retry.

## Notes

- This command never modifies the keystore. Re-keying is a manual `keytool` step.
- If the SPA itself changed, use `/deploy-test-frontend` or `/deploy-prod-frontend`
  separately — those rebuild the SPA and publish **only that env's** APK + manifest from
  `frontend/public/downloads/` (test → `kis-attendance-test.apk`, prod → `kis-attendance.apk`)
  under the stable name; they never delete a server's APK when the local one is missing.

## Notes (Session 19)
- **Deploy before you build.** Every `/deploy-test*` re-publishes the repo's `frontend/public/downloads/<env APK>` + manifest; build the new APK after the deploy (or the deploy republishes the previous one — harmless if it is the same build).
- **Landing on an exact versionName:** the build bumps the patch (`X.Y.Z → X.Y.Z+1`). To ship exactly `1.4.0`, set `versionName=1.4.-1` first (bash arithmetic turns it into `1.4.0`); commit `android/version.properties` after the build (`chore(android): TEST app X.Y.Z (build N)`).
- **Release-build check:** every `in.kisschool.data.api.dto.* -> ` line in `app/build/outputs/mapping/<flavor>Release/mapping.txt` must map to itself; data persisted outside the dto package (saved accounts) uses org.json, not Gson (Gotcha #16).
- Each TEST upload force-updates every phone with the TEST app (`min_version_code` = the new build); a prod upload does the same for every teacher — prod only with the owner's explicit go-ahead.
