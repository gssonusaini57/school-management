---
name: project_prod_deployment_kisschool
description: "school-management PRODUCTION is live at kisschool.in (served at domain ROOT), separate from the /school/ TEST box"
metadata: 
  node_type: memory
  type: project
  originSessionId: ef13f4d1-04c7-4142-92f5-05bda9964d1f
---

Deployed 2026-05-29. KIS School Management now has a **production** environment at **https://kisschool.in**, served at the **domain root** (clean URLs), distinct from TEST which stays at `https://expressonly.in/school/`.

- **Prod server:** `69.62.72.137` (Ubuntu 24.04), user `root`, SSH key `~/.ssh/enamfoss_prod`. **Shared box** — also runs a Java/Tomcat "enamfoss" Angular app (`/etc/nginx/conf.d/enamfoss.conf`, `server_name 69.62.72.137`, port 8080). Our vhost `server_name kisschool.in www.kisschool.in` coexists; do not touch enamfoss.
- **URL layout (prod ROOT):** `/` public site · `/admin/` React SPA · `/api/` FastAPI · `/downloads/` APK. TEST keeps the `/school/...` subpath.
- **Same source, both targets** — base path is build-time parametrized with test-preserving defaults. Knobs live in `scripts/deploy/<env>/env.sh`: `VITE_BASE`, `VITE_API_URL`, `SITE_BASE_PATH`, `HEALTH_PATH`, `SITE_URL_PATH`. Consumed by `scripts/deploy/common/lib.sh`. PROD = `/admin/`,`/api/`,``(empty),`/api/health`,`/`. TEST = `/school/admin/`,`/school/api`,`/school`,`/school/api/health`,`/school/`. See [[feedback_vite_base_parametrization]].
- **nginx:** dedicated vhost `deploy/nginx.kisschool.conf` → `/etc/nginx/conf.d/kisschool.conf` (nginx 1.24: `listen 443 ssl http2;`, not `http2 on;`). SSL via Let's Encrypt `certbot certonly --nginx -d kisschool.in -d www.kisschool.in` (expires 2026-08-27, auto-renew). www→apex + http→https redirects.
- **MySQL** was installed fresh (`mysql-server` 8.0.45) — provision scripts don't install it. Root password saved at `/tmp/kis_prod_mysql_root_pw.txt` on the dev mac (ephemeral — store in 1Password). DB `school_management` + user `school` created by provision step 03; `.env` has `CORS_ORIGINS=https://kisschool.in` + server-generated JWT_SECRET.
- **Deploy:** `bash scripts/deploy/prod/deploy-all.sh` (backend+frontend) then `bash scripts/deploy/prod/deploy-public-site.sh` (new). Both gate on typing `DEPLOY PROD`.
- **Mobile:** Android app rebranded to package **`in.kisschool`** with `prod`/`staging` product flavors (per-flavor `BuildConfig.API_BASE_URL`). iOS source repointed but IPA build deferred (needs xcodegen + Apple Dev account). See [[project_android_teacher_app]].
- **Admin logins (Session 16):** changed from `@kis.com`/`@kisschool.in` to **`nsnishasaini57@gmail.com`** (admin) / **`gssonusaini57@gmail.com`** (super-admin) — hardcoded in `backend/app/routers/auth.py`. admin password = `admin123`; super-admin password was CHANGED from `super123` (unknown — reset if needed). TEST and PROD now share identical admin/super-admin `password_hash` (copied test→prod) + identical SMTP creds.
- **Email (Zoho):** SMTP configured on BOTH servers (`smtp.zoho.in:465`, `info@kisschool.in`) so forgot/reset-password emails actually send. Prod `.env` has `APP_BASE_URL=https://kisschool.in/admin` so reset links are correct. See [[project_staff_temp_password]].
- Both servers fully **code-synced** (Session 16): test brought to migrations 0010/0011 + gmail admin emails + temp-password + forgot-password. Prod migrations at head `0011_password_reset_tokens`.

Provisioning gotcha: `provision.sh`'s `confirm` prompt eats piped stdin via an earlier `ssh` call — run the numbered `scripts/provision/0[1-5]-*.sh` directly with `</dev/null` instead. Skip step 06 on prod (it installs the `/school/` snippet; prod uses the standalone vhost).
