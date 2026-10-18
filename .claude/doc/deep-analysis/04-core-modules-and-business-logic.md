# 04 · Core Modules and Business Logic

> Index: [README.md](README.md) · Previous: [03-folder-structure-guide.md](03-folder-structure-guide.md) · Next: [05-execution-and-data-flow.md](05-execution-and-data-flow.md)

## Backend layering

The backend has no repository or service layer in the classic sense. Routers talk to
SQLAlchemy models directly; the two places where logic is pure and reusable are
`services/results.py` and `pdf/builder.py`.

```
   HTTP ──▶ middleware.py ──▶ routers/*.py ──▶ schemas/*.py (validate in / serialise out)
                                   │
                                   ├──▶ deps.py          who is calling, what may they touch
                                   ├──▶ models/*.py      read & write rows (SQLAlchemy Session)
                                   ├──▶ services/results.py   pure aggregation (no DB)
                                   ├──▶ pdf/render_or_cache.py ─▶ pdf/builder.py (pure) ─▶ pdf/render.py (WeasyPrint)
                                   ├──▶ events.py        publish after commit
                                   ├──▶ notifications.py ─▶ mailer.py  (after commit, never raises)
                                   └──▶ logging_config.py  structured audit events
```

## Core (shared) modules — `backend/app/*.py`

| Module | Owns | Key functions / objects | Used by |
|---|---|---|---|
| `config.py` | all runtime settings from `.env` | `Settings`, `settings`; derived properties `smtp_from_address`, `approver_notify_email`, `email_logo_url`, `email_enabled` | everything |
| `db.py` | engine + session factory | `engine`, `SessionLocal`, `Base`, `get_db` | models, routers, `alembic/env.py`, `main.lifespan` |
| `security.py` | password hashing, JWT, reset-token hashing | `hash_password`, `verify_password`, `create_token(sub, role, name, allowed_classes, allowed_menus)`, `decode_token`, `generate_reset_token` | `routers/auth.py`, `routers/staff.py`, `deps.py`, `middleware.py` |
| `deps.py` | request-scoped identity and authorisation | `CurrentUser` dataclass; `current_user` (Bearer), `current_user_sse` (`?token=`), `require_admin` (admin **or** super-admin), `require_super_admin`, `assert_class_allowed(user, class_name)`, `db_dep` | every router |
| `constants.py` | canonical class list and the "All" sentinel | `CLASSES`, `is_all_sentinel`, `expand_classes` | `routers/auth.py` (login), `deps._parse` (decode) |
| `permissions.py` | staff menu-grant registry | `MENU_KEYS`, `DEFAULT_STAFF_MENUS`, `sanitize_menus` | `routers/staff.py` |
| `events.py` | SSE fan-out | `Broker.publish(channel, event, **payload)`, `Broker.subscribe(channel)`; module-level `broker` | mutating routers, `routers/stream.py` |
| `logging_config.py` | JSON/text logging, rotating files, request context vars | `configure_logging`, `get_logger`, `request_id_ctx`, `user_sub_ctx`, `user_role_ctx` | `main.py`, `middleware.py`, all routers (`app.audit.*` loggers) |
| `middleware.py` | per-request context + access log | `RequestContextMiddleware` (sets `X-Request-ID`, decodes the token for logging only) | `main.py` |
| `mailer.py` | one SMTP send | `send_email(to, subject, html, text)`, `EmailNotConfigured` | `notifications.py`, `routers/auth.py` |
| `email_templates.py` | branded HTML email bodies | `password_reset_email`, `student_edit_request_email`, `marks_edit_request_email`, `marks_batch_submitted_email`, `request_outcome_email` | `notifications.py`, `routers/auth.py` |
| `notifications.py` | fail-safe workflow emails | `notify_student_edit_request`, `notify_marks_edit_request`, `notify_marks_submitted` (defined, **never called** — see 08), `notify_request_outcome`; decorator `_never_raises` | `routers/students.py`, `edit_requests.py`, `marks_batches.py` |
| `main.py` | app assembly | `lifespan` (seeds the two admin rows), middleware order, router registration order | gunicorn |

## Routers — `backend/app/routers/`

All prefixes are under `/api` (added in `main.py`). "Auth" is the FastAPI dependency
on the handler; "scope" means `assert_class_allowed` is applied for staff.

| Router | Prefix | Endpoints (method path) | Auth / scope | Publishes | Notable rules |
|---|---|---|---|---|---|
| `health.py` | — | `GET /health` | none | — | used by deploy health checks |
| `auth.py` | `/auth` | `POST /login`, `POST /change-password`, `POST /forgot-password`, `POST /reset-password`, `POST /logout`, `GET /me` | login/forgot/reset public; change-password admin roles; others any user | — | three login branches (super-admin email constant, admin email constant, staff by email or digits-normalised phone); staff accept real **or** temp password; `expand_classes` before minting; forgot-password always answers the same message (no account enumeration); reset tokens stored as SHA-256, single-use, 30 min |
| `students.py` | `/students` | `GET ""` (paginated, filters `class`, `q`, `status`, `include_deleted`), `GET /{sid}`, `POST ""`, `PATCH /{sid}`, `DELETE /{sid}`, `POST /{sid}/documents/{kind}`, `POST /bulk-import` | any user + scope; bulk-import admin | `students`, `dashboard`, `edit_requests`, `deletion_requests` | `admission_id = KIS/{year}/{no:04d}`; pre-flight uniqueness → 409 with the conflicting name; PATCH by super-admin applies, by others is queued as a diff (one pending per student); DELETE is a state transition, never a row delete; bulk import is all-or-nothing |
| `files.py` | `/files` | `GET /students/{sid}/{kind}`, `GET /students/{sid}/{kind}/inline` | any user + scope (Bearer vs `?token=`) | — | streams `student_documents.data` with its stored MIME type |
| `attendance.py` | `/attendance` | `GET ""`, `PUT ""`, `DELETE ""`, `GET /today-summary`, `GET /marked-dates`, `POST /bulk-import` | any user + scope | `dashboard` | PUT replaces the day's records; holiday → no records; summary counts `H` separately; bulk import accepts only `P/A/L` |
| `marks.py` | `/marks` | `POST /bulk` (legacy, `batch_id` NULL), `GET /results` (new), `GET ""` (legacy pivot), `POST /bulk-import` (legacy) | any user + scope | — | `/results` loads subjects+components, roster, marks for `(class, session)` and calls `aggregate_class_results`; includes draft marks |
| `marks_batches.py` | `/marks/batches` and `/admin/marks-edit-requests` | `GET ""`, `POST ""`, `POST /{id}/submit`, `POST /{id}/request-edit`; queue: `GET ""`, `POST /{rid}/approve`, `POST /{rid}/reject` | any user + scope; queue super-admin | `marks_batches`, `marks_edit_requests` | save = upsert rows + delete rows the client dropped; submitted batches reject saves from non-super-admins (409); super-admin may not file requests (403); approve flips `submitted → draft` |
| `fees.py` | `/fees` | `GET ""`, `POST ""`, `DELETE /{fid}` | list any user (scope only when `class` given); writes admin | `fees`, `dashboard` | receipt number defaults to `RC<ms>`; student name denormalised |
| `notices.py` | `/notices` | `GET ""`, `POST ""`, `DELETE /{nid}` | list/create any user; delete admin | `notices`, `dashboard` | — |
| `staff.py` | `/staff` | `GET ""`, `POST ""`, `PATCH /{sid}`, `POST /change-password`, `POST /{sid}/temp-password`, `DELETE /{sid}/temp-password`, `DELETE /{sid}`, `POST /bulk-import` | admin, except `change-password` which is staff-only | `staff`, `deletion_requests` | 6-digit numeric initial password returned once; `employee_id` sequence per year; `reset_password` flag issues a new one; bulk import returns `credentials[]`; empty `assigned_classes` on import → `["All"]` |
| `reports.py` | `/reports` | `GET /class-wise`, `/fee-summary`, `/attendance-monthly`, `/staff-list` | admin | — | plain dict responses; **do not filter soft-deleted rows** (08) |
| `class_subjects.py` | `/class-subjects` | `GET ""`, `GET /{id}`, `POST ""`, `PATCH /{id}`, `DELETE /{id}`, `POST /bulk-import`, `POST /seed-defaults`, `POST /{id}/components`, `PATCH /components/{cid}`, `DELETE /components/{cid}`, `PUT /{id}/components` | reads any user; writes super-admin | `class_subjects` | seed refuses if any subject exists; `PUT …/components` replaces atomically and rejects duplicate names |
| `deletion_requests.py` | `/admin/deletion-requests` | `GET ""`, `POST /{kind}/{rid}/approve`, `POST /{kind}/{rid}/restore`, `DELETE /{kind}/{rid}` | super-admin; restore also admin | `students`/`staff`, `deletion_requests`, `dashboard` | purge only from `deleted` (two-step by design); purge relies on FK `CASCADE` |
| `edit_requests.py` | `/admin/edit-requests` | `GET ""`, `POST /{rid}/approve`, `POST /{rid}/reject` | super-admin | `edit_requests`, `students`, `dashboard` | approve re-validates the diff through `StudentUpdate` and re-checks uniqueness; `updated_by` records "super-admin (approved <requester>)" |
| `pdf.py` | `/pdf` | `POST /{kind}` | any user | — | validates against `SCHEMA_BY_KIND`; `report-card`/`pseb-admit-card` → 410 Gone; WeasyPrint missing → 503 |
| `pdf_templates.py` | `/pdf/templates` and `/pdf/cache` | templates CRUD, `GET/PUT /{id}/student-data`, `DELETE /{id}/student-data/{sid}`, `GET /{id}/students`, `POST /{id}/render`; cache `GET /{pdf_id}`, `GET /{pdf_id}/inline` | admin; cache reads any user | — | PATCH bumps `version`; student-data upsert bounded to the template's class; render loops `render_or_cache` per student |
| `stream.py` | `/stream` | one `GET` per channel | `?token=` | — | `EventSourceResponse(ping=15)` |
| `_bulk.py` | (helper) | `read_csv` (BOM-safe), `parse_date_field` (ISO + Indian formats), `must_str`/`opt_str`/`must_int`/`opt_int`/`must_choice`, `FieldError`, `error_dict`, `title_case` | — | — | shared contract: `{inserted, errors[{row, field, value, reason, data}], aborted}` |

## Data model — `backend/app/models/`

```
 admin_auth(1)   super_admin_auth(1)        password_reset_tokens
                                            (account_type, account_ref, token_hash UNIQUE, expires_at, used_at)

 staff ─────────────< staff_classes (staff_id, class_name)  ← "All" sentinel row possible
   │ email UNIQUE, employee_id UNIQUE, password_hash, temp_password_hash,
   │ allowed_menus JSON, status + 5 soft-delete columns

 class_subjects ──────< subject_exam_components
   (class_name, subject_name) UNIQUE        (class_subject_id, component_name) UNIQUE
   category ENUM                             max_marks, order_index, term 1|2|NULL
         ▲ string match only: marks.subject == subject_name AND marks.exam_type == component_name

 students ─────< student_documents  (student_id, kind) UNIQUE, data LONGBLOB
   │ admission_id UNIQUE, (class_name, roll_no) UNIQUE, status + soft-delete columns
   ├────────< attendance_records >──── attendance  (class_name, date) UNIQUE, is_holiday
   ├────────< marks  (batch_id, student_id) UNIQUE; batch_id NULL = legacy
   │              └──> marks_batches (class_name, subject, exam_type, session) UNIQUE, status draft|submitted
   │                        └────< marks_edit_requests (reason NOT NULL, status, reviewed_*)
   ├────────< fee_payments  receipt_no UNIQUE, student_name denormalised
   ├────────< student_edit_requests  changes JSON {field:{old,new}}, status
   ├────────< pdf_student_data  (kind, student_id, session, term_key) UNIQUE, data JSON
   └────────< pdf_cache  (kind, student_id, template_id, template_version) UNIQUE, source_hash, data LONGBLOB
                   └──> pdf_templates  (kind, class_name, session, term_key) UNIQUE, version, data JSON
 notices (standalone)
```

Foreign-key behaviour worth memorising: every child of `students` cascades on delete
(documents, attendance records, marks, fees, edit requests, PDF data and cache);
`marks.batch_id` is `SET NULL` when a batch is deleted; `marks_edit_requests` and
`subject_exam_components` cascade from their parents. **`class_name` is never a foreign
key** — it is a string compared against the hand-mirrored `CLASSES` list.

Enum columns are stored as plain `VARCHAR` with `native_enum=False` and
`values_callable` so the `.value` (e.g. `pseb-admit-card`) is persisted rather than the
Python attribute name (Gotcha 8). `RecordStatus` (`active`, `pending_delete`,
`deleted`) is shared by `staff` and `students`.

## Pure domain logic

| Module | Inputs | Outputs | Why it is separate |
|---|---|---|---|
| `services/results.py` | `ClassSubject` rows with components, `Marks` rows, roster ids, a `Scope` | `ClassResults` / per-student `(subjects, total, max, pct, grade)`; `grade_for`, `scope_from_term` | the on-screen table and the printed report card must never disagree; both call this |
| `pdf/builder.py` | template `data` JSON, `Student`, per-student JSON, marks + subjects | validated `ReportCard` / `PsebAdmitCard` Pydantic models | keeps template merging testable without a DB or WeasyPrint |
| `pdf/schemas.py` | — | payload models per kind; `TEMPLATE_SCHEMA_BY_KIND`, `STUDENT_DATA_SCHEMA_BY_KIND` | the JSON columns are validated on write, so templates can trust their shape |
| `pdf/format.py` | numbers / dates | `₹ 1,00,000.00`, `08 May 2026`, `08-05-2026`, `April 2026` | mirrors `frontend/src/lib/format.ts` so screen and print match |
| `pdf/render.py` | kind + dict | HTML, then PDF bytes | WeasyPrint is imported lazily so a missing system library breaks one route, not startup |
| `pdf/render_or_cache.py` | `PdfTemplate`, `student_id`, `force` | `{student_id, status: cached|rendered|error, pdf_id, error}` | the only PDF module that touches the DB; computes `source_hash` **before** the cache lookup |

## Frontend modules — `frontend/src/`

| Module | Responsibility | Depends on |
|---|---|---|
| `lib/api.ts` | axios instance (`VITE_API_URL`), Bearer interceptor from `sessionStorage`, 401 → clear + redirect to `${BASE_URL}login`, `apiError()`, `fileUrl()` for inline documents | — |
| `lib/auth.ts` | `AuthUser` in `sessionStorage` (`kis_user`), `useAuth()` (`isAdmin` true for both admin roles, `isSuperAdmin`), `canAccessMenu`, remember-me in `localStorage` | `api.ts`, `menus.ts` |
| `lib/sse.ts` | `useSSE(channel, keysToInvalidate)` opens an `EventSource` and invalidates TanStack queries on every message | `api.ts` |
| `lib/version.ts` | `useVersionCheck()` polls `version.json` every 5 min while visible; reloads with `?_v=` on mismatch | Vite `__BUILD_ID__` |
| `lib/menus.ts`, `lib/nav-sections.ts`, `lib/nav-mode.ts` | menu-key registry (mirror of `permissions.py`); the single `SECTIONS` registry with `adminOnly` / `superAdminOnly` / `menuKey` flags and `filterAccessibleSections`; topbar-vs-sidebar persisted in `localStorage` `kis.nav.mode` | `auth.ts` |
| `lib/i18n.ts` | i18next with `en`/`pa` built from the design-system JSON; persists `kis.locale`; sets `<html lang>` | `packages/design-system/i18n/*` |
| `lib/pdf.ts` | `downloadPdf(kind, payload, filename)` for ad-hoc kinds; `cachedPdfUrl` / `downloadCachedPdf` for templated output | `api.ts` |
| `lib/templates.ts` | CSV header + sample rows for the five bulk-import dialogs | — |
| `lib/utils.ts`, `lib/format.ts`, `lib/compress.ts`, `lib/student-labels.ts` | `cn`, `CLASSES`, `RELIGIONS`, `toTitleCase`, `digitsOnly`, `dobBounds`; INR/date formatting; client-side JPEG compression (900 px, q 0.75); field labels for the edit-request diff viewer | — |
| `components/ProtectedRoute.tsx` | redirects unauthenticated users to `/login`, bounces `superAdminOnly` / `adminOnly` / `menuKey` violations to `/dashboard` | `auth.ts` |
| `components/Layout.tsx` + `Sidebar.tsx` + `TopNav.tsx` | chrome: slim topbar, user menu, locale switch, nav-mode toggle; both navigations render `SECTIONS` | `nav-sections.ts`, `nav-mode.ts` |
| `components/BulkImportDialog.tsx` | template download, upload, sticky error table, error-report CSV | `api.ts` |
| `components/T.tsx`, `LocaleSwitch.tsx` | `<T k>` translation element with `lang` attribute; bilingual heading/body; EN/ਪੰਜਾਬੀ toggle | `i18n.ts` |
| `types/api.ts` | TypeScript mirror of every response shape | — |

### Pages and the endpoints they call

| Page | Reads | Writes | SSE |
|---|---|---|---|
| `Dashboard.tsx` | `/students?page_size=1000`, `/staff`, `/fees`, `/notices`, `/attendance/today-summary` | — | `dashboard` |
| `Admissions.tsx` | — | `POST /students`, `POST /students/{id}/documents/{kind}` | — |
| `Students.tsx` | `/students` (paged, URL-driven filters) | `DELETE /students/{id}`, bulk import | `students` |
| `StudentDetail.tsx` | `/students/{id}`, `/files/.../inline` | `PATCH /students/{id}`, documents | — |
| `Attendance.tsx` | `/students?class=&page_size=500`, `/attendance` | `PUT /attendance`, `DELETE /attendance`, bulk import | — |
| `MarksEntry.tsx` | `/class-subjects?class=`, `/class-subjects/{id}`, `/students`, `/marks/batches` | `POST /marks/batches`, `/submit`, `/request-edit`, legacy bulk import | `marks_batches` |
| `MarksResults.tsx` | `/marks/results?class=&session=&scope=` | — | — |
| `Fees.tsx` | `/fees`, `/students?class=&page_size=500` | `POST /fees`, `DELETE /fees/{id}`, ad-hoc `POST /pdf/fee-receipt` | `fees` |
| `Notices.tsx` | `/notices` | `POST`, `DELETE` | `notices` |
| `Staff.tsx` | `/staff` | `POST`, `PATCH`, `DELETE`, temp-password, bulk import | `staff` |
| `Reports.tsx` | `/reports/*` | — | — |
| `Letterheads.tsx`, `SalarySlips.tsx` | — | `POST /pdf/{kind}` | — |
| `Templates.tsx`, `TemplateDetail.tsx` | `/pdf/templates`, `/{id}`, `/{id}/students`, `/{id}/student-data` | `POST`/`PATCH`/`DELETE` templates, `PUT` student data, `POST /render`, cache download | — |
| `ClassSubjects.tsx`, `ClassSubjectDetail.tsx` | `/class-subjects`, `/{id}` | CRUD, seed, `PUT /{id}/components` | `class_subjects` |
| `DeletionRequests.tsx`, `EditRequests.tsx` | `/admin/deletion-requests`, `/admin/edit-requests`, `/admin/marks-edit-requests` | approve / reject / restore / purge | `deletion_requests`, `edit_requests`, `marks_edit_requests` |
| `Login.tsx`, `ForgotPassword.tsx`, `ResetPassword.tsx` | — | `POST /auth/login`, `/forgot-password`, `/reset-password` | — |
| `MobileApps.tsx` | — | — | — |

## Mobile clients

**Android** (`android/app/src/main/java/in/kisschool/`): `KisApp` creates one
`AppContainer`; `MainActivity` wraps everything in `UpdateGate` and chooses the start
route (login / forced password change / home). `ApiService` mirrors the backend
contract (`auth/login`, `auth/me`, paged `students`, `students/{id}` with pending-edit
metadata, PATCH + DELETE-with-body, document upload, attendance, `marked-dates`,
class-subjects, marks batches, approval queues, `app-version.json`). Repositories are
thin; ViewModels own screen state. `TokenStore` keeps the JWT in
`EncryptedSharedPreferences`.

**iOS** (`ios/KisAttendance/`): `ApiClient` (singleton, Keychain-backed `AuthStore`)
covers login, change/forgot password, `me`, students, attendance; UI stops at the
Session 7 screens. It is **not** a feature-complete mirror of Android today.

## Permission matrix (derived from the dependencies and checks in the routers)

| Capability | staff | admin | super_admin |
|---|---|---|---|
| Read students / documents | own classes only | all | all, plus `include_deleted` |
| Create student, upload documents | own classes | yes | yes |
| Edit student | queued for approval | queued for approval | applied immediately |
| Delete student | request (`pending_delete`), own classes | request | archive directly; approve / purge |
| Restore an archived record | no | yes | yes |
| Attendance read / save / clear | own classes | all | all |
| Marks batch save / submit | own classes | all | all, including locked batches |
| File a marks edit request | yes | yes | **no** (403: edit directly) |
| Approve / reject marks edit requests | no | no | yes |
| Results table | own classes | all | all |
| Fees: list | yes (scoped only if a `class` filter is sent) | yes | yes |
| Fees: create / delete | no | yes | yes |
| Notices: list / post | yes | yes | yes |
| Notices: delete | no | yes | yes |
| Staff accounts, menus, temp passwords | no | yes | yes |
| Change own password | `POST /staff/change-password` | `POST /auth/change-password` | `POST /auth/change-password` |
| Reports | no | yes | yes |
| Class-subjects master: read | yes | yes | yes |
| Class-subjects master: write / seed | no | no | yes |
| Ad-hoc PDF render (`POST /pdf/{kind}`) | yes at the API; UI hidden unless menu granted | yes | yes |
| PDF templates CRUD / bulk render | no | yes | yes |
| Download a cached PDF by id | yes (authentication only, no ownership check) | yes | yes |
| Deletion-request queue | no | restore only | list / approve / purge |
| Student edit-request queue | no | no | yes |
| SSE channels | yes | yes | yes |

The portal additionally hides menus from staff according to `allowed_menus`
(defaults: dashboard, students, attendance, marks-entry, marks-results, notices,
mobile-apps). That is a convenience filter, not security: the API decides.

## Import rules to preserve

* `routers/*` may import `deps`, `schemas`, `models`, `events`, `notifications`,
  `services`, `pdf`, `constants`, `permissions`, `logging_config`, `_bulk`.
* `services/results.py` and `pdf/builder.py` import **no** database code.
* `models/*` import only `db.Base` and sibling model modules (`record_status`).
* Nothing imports from `routers` except `main.py` — the one exception is
  `routers/edit_requests.py` reusing `_compute_admission_id` and `_check_uniqueness`
  from `routers/students.py`. If you need a third consumer, move those helpers to a
  `services/students.py`.

> Next: [05-execution-and-data-flow.md](05-execution-and-data-flow.md) — how a request actually runs.
