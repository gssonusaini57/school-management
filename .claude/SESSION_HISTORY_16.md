# Session 16 — 2026-06-06 · PROD launch at kisschool.in + Android `in.kisschool` rebrand + temp-password + forgot-password

**Focus:** Stand up a dedicated production environment and a batch of cross-cutting features.

**(A) PROD at kisschool.in (served at ROOT).** New dedicated domain on a SHARED box `69.62.72.137` (key `~/.ssh/enamfoss_prod`) that already runs a Java/Tomcat "enamfoss" app (bare-IP vhost). Installed MySQL 8 + certbot; new **standalone** nginx vhost [deploy/nginx.kisschool.conf](../deploy/nginx.kisschool.conf) (`/`=public site, `/admin/`=SPA, `/api/`=FastAPI, `/downloads/`). **Base-path parametrized** so one source ships to TEST (`/school/...`) and PROD (root): `VITE_BASE`/`VITE_API_URL`/`SITE_BASE_PATH`/`HEALTH_PATH`/`SITE_URL_PATH` in `scripts/deploy/<env>/env.sh`, consumed by `common/lib.sh`; `vite.config.ts` base + `public-site/src/_data/site.cjs` basePath read env (test defaults) — see Gotcha #17. Filled `scripts/deploy/prod/env.sh`; added `scripts/deploy/prod/{deploy-public-site,upload-apk}.sh`. **Migrated master data** test→prod (staff+staff_classes, students+documents, class_subjects+subject_exam_components) via streamed mysqldump.

**(B) Android `in.kisschool` rebrand + features.** Package renamed `com.expressonly.kisattendance → in.kisschool` (backtick-escaped `in` keyword everywhere). **Product flavors** `prod` (`in.kisschool`, kisschool.in/api) + `staging` (`in.kisschool.test`, expressonly.in/school/api) via `BuildConfig.API_BASE_URL`; `build-android.sh {prod|test}` + force-update gate ([release-android](./commands/release-android.md) publishes `app-version.json`). New app screens: **Login** redesigned to match web (gradient/crest/remember-me + Forgot-password link); **Edit Student** (full validation + staff edit-request workflow) with **document upload/preview** (Coil, photo/dob_cert/aadhar); **Marks Entry** (draft→submit→lock→request-edit). Fixed `/students` pagination DTO (Gotcha #18) and the **R8 keep-rule → login 422** bug (Gotcha #16). Both APKs rebuilt + deployed per server.

**(C) Auth: temp-password + forgot-password + gmail admin logins.** Admin/super-admin login identifiers → `nsnishasaini57@gmail.com` / `gssonusaini57@gmail.com`. **Migration 0010** staff `temp_password_hash` (admin-set 2nd credential, web Staff page; login accepts real-OR-temp). **Migration 0011** `password_reset_tokens` — forgot/reset works for admin/super-admin/staff; SMTP (Zoho `info@kisschool.in`) + `APP_BASE_URL=https://kisschool.in/admin` configured on prod; fixed web ForgotPassword form to POST `{identifier}`. See Gotcha #19. Copied admin/super-admin password hashes test→prod so both match.

**Deploys:** prod provisioned + `deploy-prod-all`/`-frontend`/`-backend`/`-public-site`; test brought to parity (`deploy-test-all` + frontend). Migrations on prod: …→0009→0010→0011. **Commits:** `79b9eed` (big), `60133ff` (forgot-form fix) on `dev` — since pushed; `origin/dev` is current through `d17113c`.

## Appendix — Promoting test → prod (HISTORICAL — prod is live)
> Kept for reference only. Prod went live in Session 16; deploy with `scripts/deploy/prod/*` + key `~/.ssh/enamfoss_prod`, or the `/deploy-prod*` commands.

1. Edit `scripts/deploy/prod/env.sh` (replace `CHANGE_ME_PROD_IP`, `CHANGE_ME_PROD_DOMAIN`).
2. `ssh-keygen -t ed25519 -f ~/.ssh/school-management_prod` then `ssh-copy-id` to prod box.
3. `SERVER=<prod-ip> SSH_KEY=~/.ssh/school-management_prod DOMAIN=<prod-domain> bash scripts/provision/provision.sh` (one-time).
4. `bash scripts/deploy/prod/deploy-all.sh` (every release).

> Moved out of CLAUDE.md on 2026-10-19 (Session 19 save).
