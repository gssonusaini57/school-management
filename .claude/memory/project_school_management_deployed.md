---
name: school-management deployed (TEST + PROD)
description: KIS School Management Portal is LIVE — PROD at https://kisschool.in (root), TEST at http://69.62.72.137/kisschool/admin/ (second instance on the prod box since 2026-10-19). Logins = gssonusaini57@gmail.com (admin) / khalsainternationalschool@gmail.com (super-admin) / staff email-or-phone.
type: project
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
**Live TEST deployment** (rebuilt 2026-10-19 — see [[project_test_instance_on_prod_box]]):
- Admin portal: http://69.62.72.137/kisschool/admin/  (Vite `base = /kisschool/admin/`, plain HTTP, no public site)
- API: http://69.62.72.137/kisschool/api/health (`{"status":"ok"}`)
- Server: 69.62.72.137 — the PROD box (also runs PROD and the enamfoss Tomcat app); key `~/.ssh/enamfoss_prod`
- Service: `systemctl status school-management-test` (gunicorn :8001, 2 workers)
- DB: MySQL `school_management_test`, user `school_test`; a clone of prod (`/sync-test-data`)
- `/opt/school-management-test/` layout: `app/`, `frontend/dist/`, `logs/`, `backups/` (700), `.env` (600)
- Files: stored as MySQL `LONGBLOB` rows, not on disk

**PROD (Session 16):** `https://kisschool.in` served at the domain ROOT — see [[project_prod_deployment_kisschool]]. Until 2026-10 TEST lived at `https://expressonly.in/school/` on 104.237.5.113 ([[project_shared_vps]], historical).

**Unified login (Session 10; admin emails changed again in commit a20133c):** `POST /auth/login` accepts `{identifier, password}` only — no role tab. Identifier may be:
- **`gssonusaini57@gmail.com`** — singleton admin (`ADMIN_EMAIL`). Password is NOT `admin123` any more (rejected on the prod clone, verified 2026-10-19) — the user knows it.
- **`khalsainternationalschool@gmail.com`** — singleton super-admin (`SUPER_ADMIN_EMAIL`); password unknown to Claude.
- A staff email OR phone (digits-normalized), now **also a staff temp password** an admin set — see [[project_staff_temp_password]].

Admin identifiers are hardcoded in [backend/app/routers/auth.py](../../../Documents/GitHub/school-management/backend/app/routers/auth.py) (`ADMIN_EMAIL`, `SUPER_ADMIN_EMAIL`). Staff credentials are stored in `staff.email` (UNIQUE) + `staff.password_hash` + `staff.force_password_change`. The legacy `access_code` model is gone — see [[staff-auth-revamp]].

See [[soft-delete-workflow]] for the role hierarchy.

**Why:** This is the project's first real deployment. Everything before this was scaffold + local builds. The reusable provisioning + deploy scripts in `scripts/provision/` and `scripts/deploy/{common,test,prod}/` are now battle-tested and idempotent.

**How to apply:**
- Subsequent deploys: `bash scripts/deploy/test/deploy-all.sh` (snapshot + auto-rollback on failure); PROD: `bash scripts/deploy/prod/deploy-all.sh` (types `DEPLOY PROD`).
- If something breaks: `bash scripts/deploy/test/rollback.sh` lists snapshots; pass a timestamp to restore.
- Don't `metadata.create_all()` from app code — always `alembic upgrade head` (deploy script does this).

**State of art (2026-05-08 late):** Frontend bundle 866 KB / 267 KB gz.

Pages: Login, Dashboard, Admissions, Students (list+detail), Attendance, MarksEntry, MarksResults, Fees, Notices, Staff, Reports, MobileApps + Stationery section: Letterheads, SalarySlips, **Templates** (list + detail with 3 sections — class-level form, per-student spreadsheet, bulk-render). Old single-shot PsebAdmitCard page removed.

Bilingual login + sidebar (Sprint 4 partial — per-page tables/forms still English). Brand fonts + tokens shared via `packages/design-system/`.

Print PDFs: 6 WeasyPrint Jinja templates in `backend/app/pdf/templates/` with shared `_base.html.j2` (tri-band header, Cinzel motto footer pinned via `position: fixed`, watermark crest). 4 ad-hoc kinds (letterheads + fee-receipt + salary-slip) hit `POST /api/pdf/{kind}`. The other 2 (`report-card`, `pseb-admit-card`) returns **410 Gone** — must use the templated flow.

**Templated PDF flow (Session 8):** 3 new tables — `pdf_templates` (per-class config, `data` JSON, `version` bumps on PATCH), `pdf_student_data` (per-student fields keyed by kind+session+term), `pdf_cache` (LONGBLOB blobs keyed by `kind, student_id, template_id, template_version`). Editing a template auto-invalidates the cache via version bump. Admin Templates page at `/admin/templates`.

React Router uses `<BrowserRouter basename={import.meta.env.BASE_URL}>` so internal links land on `<VITE_BASE><route>` (TEST `/kisschool/admin/`, PROD `/admin/`); never hardcode the prefix.
