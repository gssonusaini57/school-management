---
name: project_prod_deployment_kisschool
description: "school-management PRODUCTION is live at kisschool.in (served at domain ROOT) on 69.62.72.137 — the same box now also hosts the TEST instance under http://69.62.72.137/kisschool/"
metadata: 
  node_type: memory
  type: project
  originSessionId: ef13f4d1-04c7-4142-92f5-05bda9964d1f
---

Deployed 2026-05-29. KIS School Management now has a **production** environment at **https://kisschool.in**, served at the **domain root** (clean URLs). Since 2026-10-19 the TEST environment is a second instance on this same box at `http://69.62.72.137/kisschool/` — see [[project_test_instance_on_prod_box]].

- **Prod server:** `69.62.72.137` (Ubuntu 24.04), user `root`, SSH key `~/.ssh/enamfoss_prod`. **Shared box** — also runs a Java/Tomcat "enamfoss" Angular app (`/etc/nginx/conf.d/enamfoss.conf`, `server_name 69.62.72.137`, port 8080). Our vhost `server_name kisschool.in www.kisschool.in` coexists; do not touch enamfoss.
- **URL layout (prod ROOT):** `/` public site · `/admin/` React SPA · `/api/` FastAPI · `/downloads/` APK. TEST keeps the `/school/...` subpath.
- **Same source, both targets** — base path is build-time parametrized with test-preserving defaults. Knobs live in `scripts/deploy/<env>/env.sh`: `VITE_BASE`, `VITE_API_URL`, `SITE_BASE_PATH`, `HEALTH_PATH`, `SITE_URL_PATH`. Consumed by `scripts/deploy/common/lib.sh`. PROD = `/admin/`,`/api/`,``(empty),`/api/health`,`/`. TEST = `/school/admin/`,`/school/api`,`/school`,`/school/api/health`,`/school/`. See [[feedback_vite_base_parametrization]].
- **nginx:** dedicated vhost `deploy/nginx.kisschool.conf` → `/etc/nginx/conf.d/kisschool.conf` (nginx 1.24: `listen 443 ssl http2;`, not `http2 on;`). SSL via Let's Encrypt `certbot certonly --nginx -d kisschool.in -d www.kisschool.in` (expires 2026-08-27, auto-renew). www→apex + http→https redirects.
- **MySQL** was installed fresh (`mysql-server` 8.0.x) — provision scripts don't install it. The root password was saved at `/tmp/kis_prod_mysql_root_pw.txt` on the dev mac and is **gone** (verified 2026-10-19); MySQL admin now goes through the server's `/etc/mysql/debian.cnf` (provision step 03 falls back to it). DB `school_management` + user `school` created by provision step 03; `.env` has `CORS_ORIGINS=https://kisschool.in` + server-generated JWT_SECRET.
- **Deploy:** `bash scripts/deploy/prod/deploy-all.sh` (backend+frontend) then `bash scripts/deploy/prod/deploy-public-site.sh` (new). Both gate on typing `DEPLOY PROD`.
- **Mobile:** Android app rebranded to package **`in.kisschool`** with `prod`/`staging` product flavors (per-flavor `BuildConfig.API_BASE_URL`). iOS source repointed but IPA build deferred (needs xcodegen + Apple Dev account). See [[project_android_teacher_app]].
- **Admin logins:** hardcoded in `backend/app/routers/auth.py` — since commit a20133c **`gssonusaini57@gmail.com`** (admin) / **`khalsainternationalschool@gmail.com`** (super-admin) (Session 16 had nsnishasaini57@ / gssonusaini57@). `admin123` is **rejected** on prod (verified 2026-10-19), so both passwords are user-known only. TEST's DB is a clone, so its hashes match prod's; TEST has **no** SMTP.
- **Email (Zoho):** SMTP configured on BOTH servers (`smtp.zoho.in:465`, `info@kisschool.in`) so forgot/reset-password emails actually send. Prod `.env` has `APP_BASE_URL=https://kisschool.in/admin` so reset links are correct. See [[project_staff_temp_password]].
- Prod schema head: **`0013_component_term`** (verified 2026-10-19; last deploy snapshot 2026-06-07). dev HEAD carries 0014–0017, already rehearsed on the TEST prod-clone.

Provisioning: `provision.sh` now reads `scripts/deploy/$ENV/env.sh` (default test), prompts via /dev/tty, and honours `ASSUME_YES=1`; step 06 is a no-op for prod (`NGINX_SNIPPET` empty — prod uses the standalone vhost).
