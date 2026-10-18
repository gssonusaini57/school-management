---
name: project_test_instance_on_prod_box
description: Since 2026-10-19 TEST is a second instance of the app on the PROD box 69.62.72.137 at http://69.62.72.137/kisschool/ (plain HTTP); every server resource is an env.sh knob so the two instances never collide.
metadata:
  type: project
---

TEST moved off the old expressonly.in box (104.237.5.113 — our SSH key is rejected there since ~Oct 2026) onto the PROD server **69.62.72.137** as a fully separate second instance. Set up 2026-10-19.

| | PROD | TEST |
|---|---|---|
| URL | https://kisschool.in/ (root; `/admin/`, `/api/`, `/downloads/`) | http://69.62.72.137/kisschool/admin/ (+ `/kisschool/api/`, `/kisschool/downloads/`), plain HTTP, no public site |
| install dir / Linux user | `/opt/school-management` / `school` | `/opt/school-management-test` / `school-test` |
| unit / gunicorn | `school-management` / 127.0.0.1:8000 | `school-management-test` / 127.0.0.1:8001 |
| MySQL DB / user | `school_management` / `school` | `school_management_test` / `school_test` (grants on its own DB only) |
| nginx | standalone vhost `/etc/nginx/conf.d/kisschool.conf` | snippet `/etc/nginx/snippets/school-management-test.conf`, `include`d (one line) from the **enamfoss** bare-IP :80 vhost `/etc/nginx/conf.d/enamfoss.conf` |
| email | Zoho SMTP | **off** (no SMTP keys — the DB is a prod clone with real staff addresses) |

- Every value lives in `scripts/deploy/<env>/env.sh` (`APP_ROOT APP_USER SERVICE_NAME APP_PORT DB_NAME DB_USER BASE_URL URL_PREFIX NGINX_SNIPPET APK_LOCAL_NAME MANIFEST_NAME …`); `lib.sh`, the provision steps and the templates (`deploy/school-management.service`, `deploy/nginx.school-test.conf`, `__TOKEN__` placeholders rendered by `render_template`) only consume them. Rendering the unit with prod values is byte-identical to the live prod unit.
- Data: `bash scripts/deploy/test/sync-from-prod.sh` (`/sync-test-data`) clones prod → test on the box, then `alembic upgrade head` with the code on TEST. Logins on TEST = prod's real credentials.
- Deploy committed code while the tree is dirty: `SRC_ROOT=$(mktemp -d) && git archive HEAD backend frontend packages | tar -x -C "$SRC_ROOT" && SRC_ROOT=$SRC_ROOT bash scripts/deploy/test/deploy-all.sh` (the frontend imports `packages/design-system`, so `packages` must be in the export).
- Provisioning step 03 authenticates as MySQL admin via `MYSQL_ROOT_PASSWORD` if exported, else the server's `/etc/mysql/debian.cnf` (root-only, used in place — the prod root password file from Session 16 is gone).
- Staging Android flavour points at `http://69.62.72.137/kisschool/api/`; cleartext is allowed for that IP only via `android/app/src/staging/res/xml/network_security_config.xml`.

**Why:** the old test box became unreachable; the user chose the bare IP + `/kisschool/` prefix over HTTP (no DNS/TLS) and "same data as prod".
**How to apply:** never hardcode `/opt/school-management`, `school-management`, `8000` or `school_management` in scripts — read the knobs. Anything touching `enamfoss.conf` must stay a single include line (the enamfoss app owns that vhost). See [[project_prod_deployment_kisschool]], [[feedback_vite_base_parametrization]], [[project_shared_vps]].
