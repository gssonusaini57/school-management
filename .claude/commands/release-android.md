---
name: release-android
description: Build a signed Android APK for a chosen flavor (prod or test) and, after explicit y/N confirmation, upload just the APK file to its server — prod → kisschool.in/downloads, test → expressonly.in/school/downloads. Does NOT rebuild the SPA.
---

# Release Android APK

End-to-end "ship a new APK" command. Builds the signed release APK for the chosen
**flavor**, copies it into `frontend/public/downloads/`, and — only after the user
types `y` — uploads **just the APK file** to that flavor's server.

The app ships in two flavors (defined in `android/app/build.gradle.kts`):

| Flavor | applicationId | API base URL | Local file | Served at |
|---|---|---|---|---|
| **prod** | `in.kisschool` | `https://kisschool.in/api/` | `kis-attendance.apk` | `https://kisschool.in/downloads/kis-attendance.apk` |
| **test** (internal flavor name `staging`) | `in.kisschool.test` | `https://expressonly.in/school/api/` | `kis-attendance-test.apk` | `https://expressonly.in/school/downloads/kis-attendance.apk` |

The `.test` applicationId suffix means both can be installed on one phone. The web
"Download for Android" link points at the stable `kis-attendance.apk` filename on
each server, so the SPA never needs redeploying for an APK update.

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
3. `versionCode` auto-bumps in `scripts/build-android.sh`; `versionName` is manual in
   `android/version.properties`. Ask if they want a `versionName` bump before building.

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
> `https://<kisschool.in|expressonly.in/school>/downloads/kis-attendance.apk`?
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

Each rsyncs its APK → `/opt/school-management/frontend/dist/downloads/kis-attendance.apk`
on the matching server (prod uses key `~/.ssh/enamfoss_prod`; test uses
`~/.ssh/uploadmytds_test` — both from the respective `env.sh`). Server-side
`chown school:school` + `chmod 644` happen automatically; the script prints `curl -I`
headers as a smoke check.

## After running

- Verify: `curl -sI https://<server>/downloads/kis-attendance.apk` → `HTTP 200` and
  `Content-Length` matching the local APK.
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
  separately — those rebuild the SPA and also publish whatever APK is in
  `public/downloads/` (which, after a build, is the prod-flavor `kis-attendance.apk`).
