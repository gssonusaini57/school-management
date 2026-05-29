# Session History — Sessions 8 & 9 (archived from CLAUDE.md)

These are the inline session summaries that used to live in `.claude/CLAUDE.md` before
the Session 13 archive sweep. Linked from CLAUDE.md → ## Session History.

---

## Session 9 — 2026-05-16 · Soft-delete + super-admin approval workflow + /check-logs

**Focus:** Replace one-click hard-delete on Students and Staff with a two-tier approval workflow (admin/staff request → super-admin approve/restore/purge). Fix LogRecord crash found in server logs. Ship `/check-logs` slash command.

**Backend** ([alembic/0003_soft_delete_workflow.py](../backend/alembic/versions/0003_soft_delete_workflow.py)):
- New `super_admin_auth` singleton table (mirrors `admin_auth`, seeded via lifespan, default `super123` from `SUPER_ADMIN_DEFAULT_PASSWORD`).
- 6 soft-delete columns on `students` + `staff`: `status` ENUM('active','pending_delete','deleted'), `delete_requested_at/by`, `delete_reason`, `deleted_at/by`. Shared enum at [models/record_status.py](../backend/app/models/record_status.py). Inline (non-native) ENUM per Gotcha #12.
- [deps.py](../backend/app/deps.py): `require_admin` accepts both `admin` + `super_admin`; new `require_super_admin`; `assert_class_allowed` exempts super-admin.
- [auth.py](../backend/app/routers/auth.py) login routes by username (`superadmin` → super_admin singleton, `admin` → admin singleton). No Login UI change.
- DELETE rewritten in [students.py:139](../backend/app/routers/students.py#L139) + [staff.py](../backend/app/routers/staff.py): staff+admin → `pending_delete` (optional `{reason}` body, staff scoped by class); super-admin → `deleted` directly. 409 if already pending/deleted.
- New [routers/deletion_requests.py](../backend/app/routers/deletion_requests.py) at `/api/admin/deletion-requests`: GET list / POST `{kind}/{id}/approve` (super-admin) / POST `{kind}/{id}/restore` (admin OR super-admin) / DELETE `{kind}/{id}` purge (super-admin AND status must be `deleted` — forces two-step).
- GET `/students` + `/staff` hide `deleted` rows by default; `?include_deleted=true` works only for super-admin. `pending_delete` rows stay visible with badge.
- New SSE channel `deletion_requests`.
- **LogRecord crash fixed** — `extra={..."name":...}` → `student_name`/`staff_name`. See Gotcha #16.

**Frontend:** new types ([api.ts](../frontend/src/types/api.ts) adds `super_admin`, `SoftDeleteFields`, `DeletionRequestItem`), `isSuperAdmin` helper ([auth.ts](../frontend/src/lib/auth.ts)), `superAdminOnly` prop on ProtectedRoute. [Students.tsx](../frontend/src/pages/Students.tsx) + [Staff.tsx](../frontend/src/pages/Staff.tsx) replace `confirm()` with Dialog (optional reason textarea); amber row tint + "Deletion requested" badge when pending. New [DeletionRequests.tsx](../frontend/src/pages/DeletionRequests.tsx) page (super-admin only) with Pending / Archived tables, Approve/Restore/Purge actions, SSE-driven. Sidebar entry under Administration.

**Permission matrix:**

| Role | Students DELETE | Staff DELETE | Approve | Restore | Purge |
|---|---|---|---|---|---|
| Staff | Request (own classes) | — | — | — | — |
| Admin | Request | Request | — | ✅ | — |
| Super-Admin | Archive directly | Archive directly | ✅ | ✅ | ✅ (only when `deleted`) |

**`/check-logs` slash command** ([.claude/commands/check-logs.md](./commands/check-logs.md) + `scripts/deploy/{test,prod}/check-logs.sh`): read-only 6-section SSH log streamer (status / journalctl filtered / error.log tail / Python tracebacks w/ context / access.log tail / 4xx-5xx). Shorthand windows: `30m` / `2h` / `1d` (default 1h).

**Deploys + verified:** two via `/deploy-test-all`. Snapshots: `app_20260516_211138.tgz` and `app_20260516_211530.tgz`. Bundle 877 KB / 270 KB gz (+3 KB gz). Super-admin login OK; admin login OK after SSH bcrypt reset (user-authorized — same as Session 8). Confirmed via audit: deploys do NOT change `admin_auth.password_hash`; only writers are (a) first-boot seed (guarded), (b) in-app Change Password, (c) explicit SSH UPDATE.

**Post-implementation user/linter edits (DON'T revert):**
- Students.tsx + students.py: URL-driven pagination + debounced search via `useSearchParams`, server-side `?q=&page=&page_size=`, new `StudentPage` envelope. Backend uses `or_` ilike across name/father/phone/village/admission_id.
- New optional Student columns `admission_no` (int), `admission_id` (derived `KIS/{year}/{admission_no:04d}`, UNIQUE), `roll_no` (UNIQUE per class). Pre-flight `_check_uniqueness` returns 409 with conflicting student name.
- Login.tsx: `<Navigate to="/dashboard" replace />` early return when already authenticated. The conditional return runs before `useEffect` below it (Rules-of-Hooks edge case); works in practice but flag if linter errors.

---

## Session 8 — 2026-05-08 (late) · KIS design retrofit + Stationery + class-templated bulk PDF flow

**Focus:** Apply the KIS brand handoff (tokens, fonts, bilingual i18n, brand SVGs); ship 6 brand-styled WeasyPrint PDF templates with admin generation pages; then design + implement a class-templated bulk PDF flow with server-side cache for Report Cards and PSEB Admit Cards.

**Design retrofit (Sprints 1–5 — earlier in the session):**
- `packages/design-system/` workspace with KIS tokens (Khalsa Blue / Royal Gold / Sangat Red / Vasant Cream / Deep Indigo), fonts (Playfair Display · Cinzel · Cormorant Garamond · Manrope · Noto Sans Gurmukhi), brand crest PNGs at native 5:4 aspect, en+pa i18n.
- React portal: route split, Vite `base` moved to `/school/admin/`, `LocaleSwitch` topbar, `<T>` wrapper, KIS-styled shadcn primitives.
- Public site: standalone Eleventy + Tailwind CLI build at `public-site/` deployed to nginx at `/school/`.
- nginx 4-location longest-prefix routing: `/school/api/` → FastAPI :8000, `/school/admin/` → React dist, `/school/downloads/` → APK, `/school/` → public-site dist.
- 6 PDF templates ([backend/app/pdf/templates/](../backend/app/pdf/templates/)): `_base.html.j2` shared brand frame (tri-band header `blue/gold/red`, Cinzel motto footer "VIDYA · VICHAR · SEVA · EST. 2005", watermark crest); kind-specific: letterhead-a (classic centered seal), letterhead-b (modern asymmetric with gold ribbon), fee-receipt (Format C with itemized table), report-card, salary-slip (gradient net-pay banner), pseb-admit-card.
- Admin generation pages: [Letterheads.tsx](../frontend/src/pages/Letterheads.tsx) (Format A/B picker), [SalarySlips.tsx](../frontend/src/pages/SalarySlips.tsx) (staff picker + earnings/deductions + live net-pay).
- Footer fix: `position: absolute` → `position: fixed` (Gotcha #14). Logo aspect: PNGs are 5:4, use `h-X w-auto`.

**Templated bulk PDF flow (Sprint 7 — second half of the session, the user-driven feature):**
- 3 new tables ([backend/alembic/versions/0002_pdf_templates_cache.py](../backend/alembic/versions/0002_pdf_templates_cache.py)):
  - `pdf_templates` — class-level config keyed by `(kind, class_name, session, term_key)`; `data` JSON validated by Pydantic on save; `version` bumps on PATCH.
  - `pdf_student_data` — per-student fields keyed by `(kind, student_id, session, term_key)`; one row per student per term.
  - `pdf_cache` — generated PDF blobs keyed by `(kind, student_id, template_id, template_version)`; LONGBLOB; CASCADE on template + student delete.
- Pydantic split in [backend/app/pdf/schemas.py](../backend/app/pdf/schemas.py); builder ([backend/app/pdf/builder.py](../backend/app/pdf/builder.py)) merges template + student rows + marks → validated model. Cache logic ([backend/app/pdf/render_or_cache.py](../backend/app/pdf/render_or_cache.py)) — render-on-miss → LONGBLOB. Router ([backend/app/routers/pdf_templates.py](../backend/app/routers/pdf_templates.py)) registered BEFORE legacy `pdf` router (Gotcha #13).
- Legacy `POST /api/pdf/{report-card,pseb-admit-card}` returns **410 Gone**. Frontend: [Templates.tsx](../frontend/src/pages/Templates.tsx) + [TemplateDetail.tsx](../frontend/src/pages/TemplateDetail.tsx) with 3 stacked sections (class config / per-student spreadsheet / bulk render).

**Verified E2E:** render → cached on 2nd call → PATCH bumps version → new render+pdf_id → DELETE cascades cache → legacy POST 410. Bundle: 866 KB JS / 267 KB gz. Snapshot: `app_20260508_180215.tgz`.

**Bug-fixes during the session:** WeasyPrint footer collapse (Gotcha #14), logo aspect (15), router ordering (13), SQLAlchemy Enum attribute-vs-value (12), admin password SSH-reset (user-authorised).
