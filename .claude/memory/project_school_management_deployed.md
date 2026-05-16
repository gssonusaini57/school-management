---
name: school-management deployed to test VPS
description: KIS School Management Portal is LIVE — public site at /school/, admin portal at /school/admin/, on test VPS 104.237.5.113. Class-templated bulk PDF flow (Session 8) + super-admin soft-delete workflow (Session 9).
type: project
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
**Live test deployment** (last updated 2026-05-16):
- Public site: https://expressonly.in/school/
- Admin portal: https://expressonly.in/school/admin/  (Vite `base = /school/admin/`)
- API: https://expressonly.in/school/api/health (`{"status":"ok"}`)
- Server: 104.237.5.113 (also runs uploadmytds — Tomcat at :8080, school-management gunicorn at :8000)
- Service: `systemctl status school-management` (gunicorn, 2 workers, restart on failure)
- DB: MySQL `school_management` schema, owned by user `school` (separate from uploadmytds's MySQL user)
- Files: stored as MySQL `LONGBLOB` rows, not on disk
- `/opt/school-management/` layout: `app/` (FastAPI), `frontend/dist/` (Vite build), `logs/`, `backups/` (auto-pruned >30d), `.env` (chmod 600)

**Unified login (Session 10, 2026-05-16):** `POST /auth/login` accepts `{identifier, password}` only — no role tab. Identifier may be:
- `admin@kis.com` / `admin123` — singleton admin (lazily seeded on first login attempt; rotate via `/auth/change-password`).
- `superadmin@kis.com` / `super123` — singleton super-admin.
- A staff email (e.g. `nishasaini@kis.com`) OR a staff phone (digits-normalized).

Admin identifiers are hardcoded in [backend/app/routers/auth.py](../../../Documents/GitHub/school-management/backend/app/routers/auth.py) (`ADMIN_EMAIL`, `SUPER_ADMIN_EMAIL`). Staff credentials are stored in `staff.email` (UNIQUE) + `staff.password_hash` + `staff.force_password_change`. The legacy `access_code` model is gone — see [[staff-auth-revamp]].

See [[soft-delete-workflow]] for the role hierarchy.

**Why:** This is the project's first real deployment. Everything before this was scaffold + local builds. The reusable provisioning + deploy scripts in `scripts/provision/` and `scripts/deploy/{common,test,prod}/` are now battle-tested and idempotent.

**How to apply:**
- Subsequent deploys: `bash scripts/deploy/test/deploy-all.sh` (snapshot + auto-rollback on failure).
- Going to prod: edit `scripts/deploy/prod/env.sh` (replace `CHANGE_ME_*`), generate prod SSH key, run provisioning against prod box, then `bash scripts/deploy/prod/deploy-all.sh`.
- If something breaks: `bash scripts/deploy/test/rollback.sh` lists snapshots; pass a timestamp to restore.
- Don't `metadata.create_all()` from app code — always `alembic upgrade head` (deploy script does this).

**State of art (2026-05-08 late):** Frontend bundle 866 KB / 267 KB gz.

Pages: Login, Dashboard, Admissions, Students (list+detail), Attendance, MarksEntry, MarksResults, Fees, Notices, Staff, Reports, MobileApps + Stationery section: Letterheads, SalarySlips, **Templates** (list + detail with 3 sections — class-level form, per-student spreadsheet, bulk-render). Old single-shot PsebAdmitCard page removed.

Bilingual login + sidebar (Sprint 4 partial — per-page tables/forms still English). Brand fonts + tokens shared via `packages/design-system/`.

Print PDFs: 6 WeasyPrint Jinja templates in `backend/app/pdf/templates/` with shared `_base.html.j2` (tri-band header, Cinzel motto footer pinned via `position: fixed`, watermark crest). 4 ad-hoc kinds (letterheads + fee-receipt + salary-slip) hit `POST /api/pdf/{kind}`. The other 2 (`report-card`, `pseb-admit-card`) returns **410 Gone** — must use the templated flow.

**Templated PDF flow (Session 8):** 3 new tables — `pdf_templates` (per-class config, `data` JSON, `version` bumps on PATCH), `pdf_student_data` (per-student fields keyed by kind+session+term), `pdf_cache` (LONGBLOB blobs keyed by `kind, student_id, template_id, template_version`). Editing a template auto-invalidates the cache via version bump. Admin Templates page at `/admin/templates`.

React Router uses `<BrowserRouter basename={import.meta.env.BASE_URL}>` so internal links land on `/school/admin/<route>`. Vite `base = /school/admin/`; never hardcode the prefix.
