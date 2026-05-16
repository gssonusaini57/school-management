---
name: Test VPS shared with uploadmytds
description: 104.237.5.113 (Ubuntu 24.04 LTS) hosts BOTH uploadmytds and school-management. Don't touch uploadmytds's files. nginx routes by path-prefix; MySQL has separate DBs; SSH key ~/.ssh/uploadmytds_test is reused.
type: project
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
**Test VPS facts (104.237.5.113):**
- Ubuntu 24.04 LTS, MySQL 8.0.45, nginx 1.24.0, Python 3.12.3
- Hosts uploadmytds (Tomcat on :8080, Java/Spring) AND school-management (gunicorn on :8000, FastAPI)
- Single nginx serving expressonly.in: `/AcuteNetworkTest/`, `/api/`, `/file/`, `/app/` → uploadmytds. `/school/`, `/school/api/` → school-management.
- nginx config: `/etc/nginx/sites-enabled/test-angular` is the SSL server block; school-management's `include /etc/nginx/snippets/school.conf;` lives inside that block (added at line 163).
- SSH: `~/.ssh/uploadmytds_test` is authorized for `root@104.237.5.113` and reused by both projects.
- MySQL root password: `RootSecurePass2024Test` (set by `uploadmytds/scripts/server/mysql-install.sh`). Each project has its own dedicated MySQL user — uploadmytds uses `acutenetwork`, school-management uses `school`.
- Let's Encrypt cert covers `expressonly.in` + `www.expressonly.in` + `104.237.5.113`. Reused by school-management automatically.

**Constraints to honor:**
- **Never modify uploadmytds files** in `/var/www/test-angular*/`, `/opt/pdffile/`, `/opt/tomcat/`, `/etc/systemd/system/tomcat.service`. school-management's footprint is exclusively `/opt/school-management/`, `/etc/systemd/system/school-management.service`, `/etc/nginx/snippets/school.conf`.
- **Never replace `nginx.conf` or `/etc/nginx/sites-enabled/test-angular`** — only append the include line. Provisioning step 06 uses Python with brace-depth tracking to insert into the correct (SSL) server block.
- **Don't run `mysql_secure_installation`** — it could break uploadmytds.
- **Existing nginx warnings** about "conflicting server name expressonly.in" are pre-existing in uploadmytds's config and don't affect routing. Don't try to fix them.

**How to apply:** Treat the VPS as multi-tenant. Provisioning + deploy scripts touch only school-management paths. Pre-flight inspection in `provision.sh` confirms uploadmytds is unaffected. If you're tempted to clean up "weird" config, check first whether it belongs to uploadmytds.
