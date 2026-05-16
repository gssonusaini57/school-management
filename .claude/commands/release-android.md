---
name: release-android
description: Build a fresh signed Android APK and (after explicit y/N confirmation) upload just the APK file to TEST so it goes live at /school/downloads/kis-attendance.apk. Does NOT rebuild the SPA — the web download link is already deployed.
---

# Release Android APK → TEST

End-to-end "ship a new APK" command. Builds the signed release APK, copies it into the frontend's `public/downloads/`, and — only after the user types `y` — uploads **just the APK file** to the server.

The web "Download for Android" link was deployed once (Session 6) and never needs re-pushing. Only the APK file itself changes between releases, so we use a lightweight `rsync` instead of a full Vite rebuild.

## Pre-flight

1. Confirm the keystore + properties exist:
   ```bash
   test -f android/keystore/kis-release.jks && \
   test -f android/keystore/keystore.properties \
     || { echo "ERROR: keystore missing — see android/README.md"; exit 1; }
   ```
2. `git status` for `android/` and `frontend/` — warn if dirty (don't block).
3. Show the current `versionCode` / `versionName` from `android/app/build.gradle.kts` and **ask the user whether they want to bump them** before building. If yes, edit the file with the new values they provide.

## Action

### Step 1 — Build the APK

```bash
bash scripts/build-android.sh
```

This runs `./gradlew :app:assembleRelease` and copies the signed APK to `frontend/public/downloads/kis-attendance.apk`. Expect ~3 MB output and a successful `BUILD SUCCESSFUL`.

### Step 2 — Show APK summary and ASK for upload confirmation

After the build succeeds, **stop and ask the user explicitly**:

> APK built — N.N MB at `frontend/public/downloads/kis-attendance.apk`.
> Upload to TEST so teachers can download it from `https://expressonly.in/school/downloads/kis-attendance.apk`?
> Type `y` to upload, anything else to skip.

Wait for the response. **Do not auto-upload** — every push is a real action against the live test server.

If the user types `y` (or `Y` / `yes`), proceed to Step 3. Otherwise, stop here and remind them they can upload later via `bash scripts/deploy/test/upload-apk.sh`.

### Step 3 — Upload just the APK (no SPA rebuild)

```bash
bash scripts/deploy/test/upload-apk.sh
```

Rsyncs `frontend/public/downloads/kis-attendance.apk` → `/opt/school-management/frontend/dist/downloads/kis-attendance.apk` over SSH. No Vite rebuild, no SPA assets touched. Server-side `chown school:school` + `chmod 644` happen automatically. Final step prints `curl -I` headers as a smoke check.

## After running

If the upload ran (the script itself prints the headers, but double-check):
- `curl -sI https://expressonly.in/school/downloads/kis-attendance.apk` → expect `HTTP 200` and `Content-Length` matching the local APK size.

Print a one-liner with the public download URL and the keystore-backup reminder:
> ⚠️ If you bumped versionCode/versionName, this is a new release — phones will see "Update" instead of "Install" next time they hit the link. Keystore (`android/keystore/kis-release.jks`) must remain backed up.

## Failure modes

- **Keystore missing:** stop early in pre-flight, point user at `android/README.md`.
- **`assembleRelease` failed:** surface the Gradle error (compile / resource / signing). Don't proceed to upload.
- **APK built but user said `n`:** APK is staged at `frontend/public/downloads/`. Mention they can upload later via `bash scripts/deploy/test/upload-apk.sh`.
- **Upload failed (SSH / rsync error):** surface the error; the APK file is still in place locally so they can retry.

## Notes

- This command does NOT modify the keystore. Generating / re-signing with a new key is a manual `keytool` invocation per `android/README.md`.
- The web "Download for Android" link in [Login.tsx](../../frontend/src/pages/Login.tsx) was deployed once (Session 6). It points to `/school/downloads/kis-attendance.apk` — a stable URL that doesn't change between APK versions, so the SPA never needs redeploying for an APK update.
- If the SPA itself changes (e.g. you edit Login.tsx), use `/deploy-test-frontend` separately. That deploy will also include the most recent APK from `public/downloads/`.
- For PROD, there is no `release-android-prod` yet — when prod deploy is ready, mirror this command to call a `scripts/deploy/prod/upload-apk.sh` with a `DEPLOY PROD` confirmation gate.
