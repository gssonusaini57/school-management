# Project Memory
**Last Updated:** 2026-10-19 | **Sessions:** 19 (1–16 archived or in memory; 18–19 detail in archives) | **Branch:** dev | **Stage:** ✅ **LIVE ON PROD** at https://kisschool.in since 2026-10-20 11:33 — dev `339c013`, schema **0021** (Results v2, optional subjects, role dashboards, stay-signed-in), Android prod **v1.3.4 build 25** — **and** TEST at http://69.62.72.137/kisschool/admin/ (second instance on the prod box, Gotcha #23) on the same code with staging app **v1.3.3 build 24**.
> **Admin logins (both instances):** admin `gssonusaini57@gmail.com` · super-admin `khalsainternationalschool@gmail.com` (hardcoded `ADMIN_EMAIL`/`SUPER_ADMIN_EMAIL` in auth.py since a20133c). Passwords are user-known only — `admin123` is rejected on prod (verified 2026-10-19). Staff log in by email-or-phone + password. TEST's DB is a prod clone, so every hash matches prod; TEST has no SMTP (email off). On TEST every active staff member also has an admin-set *temporary* password (value user-known, never recorded) for teacher-view testing; `/sync-test-data` wipes it.

> Slash commands: see [.claude/commands/](./commands/) — `/provision-test`, `/deploy-test*`, `/sync-test-data`, `/deploy-prod*` (incl. `/deploy-prod-public-site`), `/clean-logs`, `/check-logs`, `/release-android`, `/save-session`, `/deep-analysis`. Android APK build: `bash scripts/build-android.sh {prod|test}` (local, needs keystore).

---

## Design system (KIS brand handoff)

Handoff package at [_handoff/khalsa-international-handoff/](../_handoff/khalsa-international-handoff/); tokens / fonts / bilingual i18n / brand SVGs mirrored at [packages/design-system/](../packages/design-system/) (`tokens.css` is generated — never hand-edit). One palette across the React portal, the Eleventy public site (`public-site/`, PROD root only), the WeasyPrint PDFs (`backend/app/pdf/`) and, since Session 19, the Android app: khalsa-blue `#0E2F8E` · royal-gold `#F5C518` · sangat-red `#E11D2C` · vasant-cream `#FFF6CC` · deep-indigo `#08205C`; fonts Playfair Display · Cinzel · Cormorant Garamond · Manrope · Noto Sans Gurmukhi.

**For implementation rules (tokens / i18n / currency-date / Punjabi-fallback / Android palette) read [.claude/skills/kis-design-system/SKILL.md](./skills/kis-design-system/SKILL.md) before editing any UI or copy.**

Sprints 1–3, 5, 7 ✅ · Sprint 4 (bilingual portal) 🟡 new pages bilingual, older Students/Attendance/Fees/Staff/Reports labels English-only · Sprint 6 (STATUS.md + Lighthouse + axe) ❌ · parent app deferred. The sprint table and the class-templated PDF notes → [SESSION_HISTORY_8_9.md](./SESSION_HISTORY_8_9.md) (appendix).

## Project Overview
**KIS School Management Portal** — Internal web app for KIS (a single school).
Used daily by administrators and teachers to manage students, attendance, marks, fees, notices, and staff.

**Status (post-migration scaffold):** Firebase fully ripped out. New stack:
- **Backend:** FastAPI + MySQL (test VPS reuses uploadmytds's MySQL instance)
- **Frontend:** React + Vite + TypeScript + Tailwind + shadcn/ui
- **Sessions & meta (Session 19):** `GET /api/sessions` · `GET /api/sessions/current` · `GET /api/sessions/defaults?session=` (super-admin) · `POST /api/sessions` + `PATCH /api/sessions/{id}` (super-admin) · `GET /api/meta` (grade letters/bands, houses, classes)
- **Results v2:** `GET /api/marks/results?class=&session=&scope=term1|term2|annual&include_drafts=` (menu `marks-results`; exam groups, rank by exact %, attendance, `not_taken` for optional subjects) · `GET /api/marks/batches/summary?session=[&class=]` (submitted/draft/missing per class·subject·exam) · `POST /api/marks/batches` takes `base_batch_id` + `base_revision` (409 on a stale screen; saves without them may not remove saved marks)
- **Optional subjects:** `GET/PUT /api/class-subjects/{id}/enrollments` (PUT super-admin); class-subject responses carry `is_optional` + `enrolled_student_ids`
- **Attendance summaries:** `GET /api/attendance/class-summary?from=&to=` (per class, ≤ 92 days, half day = 0.5, caller's classes only) · `GET /api/attendance/marked-dates?class=&from=&to=` · `GET /api/attendance/today-summary`
- **Report cards v2:** `GET /api/pdf/templates/resolve?kind&class&session&scope` · `POST /api/pdf/templates/bulk-create` · `GET /api/pdf/templates/{id}/roster` · `GET …/{id}/preview` · `POST /api/pdf/templates/{id}/render-jobs` → `GET /api/pdf/render-jobs/{id}` (+ `/cancel`, `/zip`, `/zip/inline?token=`)
- **Stay signed in (Session 19):** `POST /api/auth/login` + `remember`, `device{name,platform}` → `refresh_token` (app) or HttpOnly cookie `kis_refresh` (web) · `POST /api/auth/refresh` (rotates) · `POST /api/auth/logout` (Bearer optional) · `GET/DELETE /api/auth/sessions[/{id}]` · `DELETE /api/staff/{id}/sessions` (admin) — Gotcha #25
- **Realtime:** Server-Sent Events (no Firebase listeners)
- **Auth:** JWT with bcrypt-hashed credentials (admin password + staff access codes)
- **Hosting:** PROD `https://kisschool.in` and TEST `http://69.62.72.137/kisschool/` — two instances on one VPS `69.62.72.137`
- **Old single-file `index.html`** archived at `_archive/index.firebase.html` for reference

**GitHub Repo:** https://github.com/gssonusaini57/school-management

---

## Tech Stack
| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite 6 + TypeScript 5 |
| UI | Tailwind 3 + shadcn/ui (radix-ui primitives) + lucide-react icons |
| Server state | TanStack Query 5 + EventSource (SSE) for realtime |
| Charts | Chart.js 4 + react-chartjs-2 |
| Backend | FastAPI 0.115 (Python 3.12) on gunicorn + uvicorn workers |
| ORM | SQLAlchemy 2.0 + Alembic migrations |
| Database | MySQL 8.0 on 69.62.72.137 (`school_management` prod · `school_management_test` test) |
| File storage | MySQL `LONGBLOB` rows (no filesystem, no S3) |
| Auth | JWT (PyJWT, HS256, 8h) + bcrypt (passlib) for admin password & staff access codes |
| Hosting | One VPS (69.62.72.137): nginx + units `school-management` (prod, :8000) and `school-management-test` (test, :8001) |

---

## Repo Layout
```
school-management/
├── backend/                      FastAPI (Python 3.12)
│   ├── app/
│   │   ├── main.py config.py db.py security.py deps.py events.py constants.py permissions.py notifications.py
│   │   ├── models/ schemas/ routers/   auth students attendance marks marks_batches class_subjects sessions meta
│   │   │                               pdf pdf_templates pdf_render_jobs fees notices staff reports stream files
│   │   │                               edit_requests deletion_requests health
│   │   ├── services/             results (pure engine) · report_cards · attendance_summary · sessions · roster
│   │   │                         · marks_batches · enrollments · render_jobs · device_sessions
│   │   ├── pdf/                  WeasyPrint builder, labels, templates/*.html.j2 (Gotchas #10, #24)
│   │   ├── jobs/render_job.py    detached bulk report-card runner · seed/exam_pattern.py
│   ├── alembic/versions/         0001 … 0021 (see Database Schema)
│   └── tests/                    pytest on in-memory SQLite (conftest.py, factories.py) — 261 tests
├── frontend/src/                 React 18 + Vite: pages/ components/ (report-cards/, ClassAttendanceCard/Chart …)
│                                 lib/ (api auth sse pdf session unsaved …) types/api.ts
├── android/                      Kotlin/Compose `in.kisschool` — app/src/main/java/in/kisschool/{data/{api,auth,repo,settings},
│                                 di, ui/{theme,nav,components,lock,update,screens/*}, util}; version.properties; keystore/ (gitignored)
├── ios/                          SwiftUI scaffold (XcodeGen) — far behind Android
├── packages/design-system/       tokens.css (generated) · i18n/portal-{en,pa}.json · brand/
├── public-site/                  Eleventy marketing site (PROD root)
├── deploy/                       systemd unit + nginx TEMPLATES, .env.example
├── scripts/                      build-android.sh · deploy/{common,test,prod}/ · provision/ (Gotcha #23)
├── docs/ROADMAP.md               future work (not scheduled)
├── _handoff/ _archive/           brand handoff package · old Firebase index.html
└── .claude/                      CLAUDE.md, SESSION_HISTORY_*/GOTCHAS_* archives, commands/, skills/, memory/ (= auto-memory)
```

## Live URLs
**PROD — kisschool.in (served at ROOT; shared box `69.62.72.137`, key `~/.ssh/enamfoss_prod`, coexists with the enamfoss Tomcat app):**
- Public site `https://kisschool.in/` · Admin portal `https://kisschool.in/admin/` · API `https://kisschool.in/api/` · Health `https://kisschool.in/api/health` · APK `https://kisschool.in/downloads/kis-attendance.apk`

**TEST — second instance on the PROD box (`69.62.72.137`, key `~/.ssh/enamfoss_prod`): plain HTTP, no public site, data = prod clone (`/sync-test-data`), email off:**
- Admin `http://69.62.72.137/kisschool/admin/` · API `http://69.62.72.137/kisschool/api/` · Health `…/kisschool/api/health` · APK `…/kisschool/downloads/kis-attendance.apk` (*staging* flavor) · manifest `…/kisschool/downloads/app-version-test.json`
- Until 2026-10 TEST was `https://expressonly.in/school/` on 104.237.5.113 (shared with uploadmytds); our SSH key is rejected there now.

## API Endpoints (REST + SSE)
- **Auth:** `POST /api/auth/login`, `POST /api/auth/change-password`, `POST /api/auth/logout`, `GET /api/auth/me`
- **Students:** `GET/POST /api/students`, `GET/PATCH/DELETE /api/students/{id}`
- **Documents:** `POST /api/students/{id}/documents/{photo|dob_cert|aadhar}` (multipart), `GET /api/files/students/{id}/{kind}` (Bearer) or `…/inline?token=` (for `<img>` tags)
- **Attendance:** `GET /api/attendance?class=&date=`, `PUT /api/attendance`, `GET /api/attendance/today-summary`
- **Marks (legacy):** `POST /api/marks/bulk` → **410 Gone**; `POST /api/marks/bulk-import` (admin, CSV with `session`) routes rows through the batch upsert. `GET /api/marks?class=&exam_type=` still pivots raw rows.
- **Marks (Session 13 batched workflow):**
  - `GET /api/marks/batches?class=&subject=&exam_type=&session=` — single batch + items, or null
  - `POST /api/marks/batches` — upsert (creates draft if absent; refuses submitted batch for non-super-admin → 409)
  - `POST /api/marks/batches/{id}/submit` — lock the batch
  - `POST /api/marks/batches/{id}/request-edit` — admin/staff enqueue request (body: `{reason: string}`, required)
  - `GET /api/admin/marks-edit-requests` (super-admin)
  - `POST /api/admin/marks-edit-requests/{id}/approve` — flips batch back to draft
  - `POST /api/admin/marks-edit-requests/{id}/reject` — body `{reason?}`
- **Fees:** `GET /api/fees`, `POST /api/fees`, `DELETE /api/fees/{id}` (admin only for writes)
- **Notices:** `GET/POST /api/notices`, `DELETE /api/notices/{id}` (admin only)
- **Staff:** `GET/POST /api/staff`, `PATCH/DELETE /api/staff/{id}` (admin only)
- **Reports:** `GET /api/reports/{class-wise|fee-summary|attendance-monthly|staff-list}` (admin only)
- **PDF (ad-hoc):** `POST /api/pdf/{letterhead-a|letterhead-b|fee-receipt|salary-slip}` — validates payload + renders. Calls to `/api/pdf/report-card` and `/api/pdf/pseb-admit-card` return **410 Gone** (use the templated flow below).
- **PDF templates (Session 8):**
  - `GET/POST /api/pdf/templates`, `GET/PATCH/DELETE /api/pdf/templates/{id}` (admin only)
  - `GET/PUT /api/pdf/templates/{id}/student-data`, `DELETE …/student-data/{student_id}`
  - `GET /api/pdf/templates/{id}/students` — roster + cache state for the bulk-render UI
  - `POST /api/pdf/templates/{id}/render` — body `{student_ids:[…], force?: bool}`
  - `GET /api/pdf/cache/{id}` (Bearer) or `…/inline?token=` (for `<a download>`)
- **Class subjects master (Session 13):**
  - `GET/POST /api/class-subjects` + `GET/PATCH/DELETE /api/class-subjects/{id}` (super-admin writes)
  - `POST /api/class-subjects/bulk-import` + `POST /api/class-subjects/seed-defaults` (seeds 127 subjects/654 components from the KIS PDF pattern)
  - `POST /api/class-subjects/{id}/components` + `PATCH/DELETE /api/class-subjects/components/{cid}` + `PUT /api/class-subjects/{id}/components` (atomic replace from the spreadsheet editor)
- **Realtime:** `GET /api/stream/{students|fees|notices|staff|dashboard|deletion-requests|edit-requests|class-subjects|marks-batches|marks-edit-requests}?token=<jwt>`

---

## Database Schema (MySQL `school_management`)
| Table | PK | Notable columns |
|---|---|---|
| admin_auth | id (singleton 1) | password_hash (bcrypt), updated_at |
| **super_admin_auth (Session 9)** | id (singleton 1) | password_hash (bcrypt), updated_at — seeded via lifespan, default password `super123` |
| staff | id BIGINT | name, designation, phone, access_code_hash (bcrypt), access_code_last4 + Session 9 soft-delete columns: `status` ENUM('active','pending_delete','deleted'), `delete_requested_at/by`, `delete_reason`, `deleted_at/by` |
| staff_classes | (staff_id, class_name) | normalizes legacy `assignedClasses` array |
| students | id BIGINT | all admission-form fields, dob DATE, annual_fee DECIMAL, class_name (indexed) + Session 9 same 6 soft-delete columns as staff |
| student_documents | id BIGINT | (student_id, kind) UNIQUE; data LONGBLOB; mime_type, byte_size |
| attendance | id BIGINT | (class_name, date) UNIQUE |
| attendance_records | (attendance_id, student_id) | status ENUM('P','A','L') |
| marks | id BIGINT | INDEX(class_name, exam_type); **Session 13** adds nullable `batch_id` FK → marks_batches + UNIQUE(batch_id, student_id) for upsert (NULL batch_id = legacy rows, tolerated) |
| fee_payments | id BIGINT | receipt_no UNIQUE, denormalized student_name |
| notices | id BIGINT | priority ENUM, audience |
| pdf_templates | id BIGINT | (kind, class_name, session, term_key) UNIQUE; `data` JSON validated by Pydantic on save; `version` int bumps on PATCH |
| pdf_student_data | id BIGINT | (kind, student_id, session, term_key) UNIQUE; `data` JSON; one row per student per (kind, session, term) |
| pdf_cache | id BIGINT | (kind, student_id, template_id, template_version) UNIQUE; `data` LONGBLOB; FK CASCADE on template + student |
| **class_subjects (Session 13)** | id BIGINT | (class_name, subject_name) UNIQUE; `category` ENUM('academic','co_curricular','grading'), `subject_name_pa`, `order_index` |
| **subject_exam_components (Session 13)** | id BIGINT | (class_subject_id, component_name) UNIQUE; `max_marks`, `order_index`; CASCADE on subject delete |
| **marks_batches (Session 13)** | id BIGINT | (class_name, subject, exam_type, session) UNIQUE; `max_marks`, `status` ENUM('draft','submitted'), `created_by`, `submitted_at/by` |
| **marks_edit_requests (Session 13)** | id BIGINT | FK batch_id CASCADE; INDEX(batch_id, status); `requested_by_role` ENUM, `reason` TEXT NOT NULL, `status` ENUM('pending','approved','rejected'), `reviewed_at/by/reject_reason` |
| **academic_sessions (0014)** | id | `session` UNIQUE (e.g. `2026-27`), starts_on/ends_on, term1_start/end, term2_start/end, `is_current` |
| marks.grade (0015) | — | VARCHAR(4) letter (A1…D) for grading components (max 0) |
| pdf_templates.scope / layout (0016) | — | scope `term1`/`term2`/`annual`; layout `summary`/`components` |
| **pdf_render_jobs (0017)** | id | template FK CASCADE, status queued→running→done/failed/cancelled, student_ids/results JSON, counters, heartbeat_at, worker_pid |
| marks_batches.revision (0018) | — | INT bumped on every write to the batch; a stale `base_revision` → 409 |
| *(0019, data only)* | — | cleared the v1 per-student report-card overrides |
| class_subjects.is_optional + **subject_enrollments (0020)** | id | (class_subject_id, student_id) UNIQUE, FK CASCADE both — who takes an optional subject |
| **device_sessions (0021)** | id | account_type + account_ref (= JWT sub), token_hash UNIQUE (sha256), family_id, platform, via, expires_at (30 d sliding), absolute_expires_at (180 d), rotated_at/replaced_by_id, revoked_at/revoked_reason (Gotcha #25) |

All migrations live under `backend/alembic/versions/` (`0001_initial` … `0021_device_sessions`: 0008–0009 Session 13, 0010–0011 Session 16, 0012 Session 17, 0013 Session 18, 0014–0021 Session 19). **Prod and TEST are both at 0021** (prod since 2026-10-20). **Never** call `metadata.create_all()` outside tests; always `alembic upgrade head`.

---

## Deployment (both instances on `69.62.72.137`)

Cheat sheet: [scripts/README.md](../scripts/README.md). Every server resource (install dir, Linux user, unit, port, DB, nginx snippet, URLs) is a knob in `scripts/deploy/<env>/env.sh` — Gotcha #23.

**Provision an instance (idempotent):** `bash scripts/provision/provision.sh --inspect-only`, then `bash scripts/provision/provision.sh` (`ENV=test` default, `ENV=prod` for prod; `ASSUME_YES=1` when non-interactive). MySQL admin for step 03: `MYSQL_ROOT_PASSWORD` if exported, else the server's `/etc/mysql/debian.cnf`. nginx, mysql-server and certbot are already on this box — provisioning doesn't install them.

**Deploy:** `bash scripts/deploy/test/deploy-all.sh` ships the working tree; prefix `SRC_ROOT=<export>` (from `git archive HEAD backend frontend packages`) to ship committed code only. Steps: AST-parse → `npm ci && npm run build` (Vite base from `VITE_BASE`) → snapshot (tar app + `mysqldump --no-tablespaces`) → rsync `backend/` + `dist/` (downloads/ excluded) → publish this env's APK + manifest → pip + `alembic upgrade head` → `systemctl restart $SERVICE_NAME` → health check `${BASE_URL}${HEALTH_PATH}` → auto-rollback on failure. PROD: same scripts under `scripts/deploy/prod/`, each gated by typing `DEPLOY PROD`.

**TEST data:** `bash scripts/deploy/test/sync-from-prod.sh` (`/sync-test-data`) — dumps prod (`--single-transaction`, no locks) on the box → replaces `school_management_test` → `alembic upgrade head` with TEST's code → restart.

**Working-copy deploys and APK publishing:** Gotcha #23. **Promoting to prod:** `bash scripts/deploy/prod/backup-db.sh` then `/deploy-prod-all`; the historical first-time prod steps → [SESSION_HISTORY_16.md](./SESSION_HISTORY_16.md) (appendix).

---

## Frontend Routes
SPA mounted at `VITE_BASE` (`/admin/` prod · `/kisschool/admin/` test). Routes:
`/login` (public) · `/dashboard` · `/admissions` · `/students` · `/students/:id?edit=1` · `/attendance` · `/marks/entry` · `/marks/results` · `/fees` (admin) · `/notices` · `/staff` (admin) · `/reports` (admin) · `/letterheads` (admin) · `/salary-slips` (admin) · `/templates` (admin) · `/templates/:id` (admin) · `/class-subjects` (super-admin) · `/class-subjects/:id` (super-admin) · `/sessions` (super-admin) · `/deletion-requests` (super-admin) · `/edit-requests` (super-admin — student + marks tabs) · `/mobile-apps`

Results has a `?tab=report-cards` tab; the Dashboard shows the admin marked/pending classes pie (`?attendance=pending|marked|holiday`) and the class-wise attendance chart for every role.

Sidebar sections: Main · Academic (incl. **Class Subjects** super-admin master, Session 13) · Administration · **Stationery** (Letterheads / Salary Slips / Templates) · Resources. The `Templates` page replaced the old single-shot `/pseb-admit-card` (Session 8); the per-row report-card download on MarksResults is gone, replaced by a banner pointing at /templates.

`<ProtectedRoute>` redirects unauth to `/login`; `adminOnly` guards bounce non-admin to `/dashboard`. `EventSource` carries the JWT via `?token=` query (browser EventSource cannot set headers).

---

## Realtime Pattern (SSE, replaces 8 Firestore onSnapshot listeners)
- Each mutating endpoint calls `broker.publish(channel, "upsert"|"delete", id=…)`.
- `app/events.py` holds an in-memory `asyncio.Queue` per subscriber per channel.
- Frontend `useSSE("students", [["students"]])` opens an `EventSource`, invalidates the listed TanStack Query keys on every event → query refetches.
- No Redis required; works because we have a single uvicorn worker process. **If you scale to >1 worker, switch the broker to Redis pub/sub.**

---

## Conventions / Gotchas

> Items 1–6 archived → [GOTCHAS_1_6.md](./GOTCHAS_1_6.md) (single-process broker, admin seed, staff last4-lookup, files via `?token=`, Vite base `/school/`, CORS not needed in prod).
> Items 7–12 archived → [GOTCHAS_7_12.md](./GOTCHAS_7_12.md) (TanStack staleTime, shadcn in-repo, compressImage client, LONGBLOB, Object.assign N/A, no-cache vs Vite-hash).
> Items 13–21 archived → [GOTCHAS_13_21.md](./GOTCHAS_13_21.md) (MySQL bucket, assert_class_allowed, first-boot, nginx `}server{` boundary, nginx alias + regex, /opt 755, head|bash SIGPIPE, MySQL root pwd, provisioning idempotent).
> Inline #1–#4 (older) archived → [GOTCHAS_INLINE_1_4.md](./GOTCHAS_INLINE_1_4.md) (React Router basename, `[] ?? X` truthy, leading-zero number inputs (superseded by NumberField — see #17), bulk-import errors in dialog not toast).

1. **Bulk-import endpoints share `backend/app/routers/_bulk.py`.** Helpers: `read_csv` (handles BOM), `title_case`, `parse_date_field`, `must_str`, `opt_str`. Each `/api/<entity>/bulk-import` follows the same shape — try-per-row, validate, accumulate `errors[]`, commit valid rows in one `db.commit()`. Response is always `{inserted: N, errors: [{row, reason, data}]}`. Frontend consumes via shared [BulkImportDialog](../frontend/src/components/BulkImportDialog.tsx) + per-page [templates.ts](../frontend/src/lib/templates.ts).

2. **Android release keystore is irreplaceable.** Once you ship an APK signed with `android/keystore/kis-release.jks`, every subsequent update for *every* phone with the app installed must be signed with the **same** keystore. Lose the .jks (or its password in `keystore.properties`) and you cannot ship updates — phones will refuse to install over the existing app. **Always back up both files** (1Password / Drive / encrypted USB) outside the repo. Both are gitignored (`android/keystore/*.jks`, `android/keystore/keystore.properties`). Current test keystore was generated with a 32-char hex random password; if the user ever wants to re-key for prod / Play Store, they need to commit to the new keystore from day one.

3. **Native `<input type="date">` is banned in this repo.** Browser-native date pickers had two real bugs users hit: (a) Safari's mm/dd/yyyy subfield Tab-trap, (b) year navigation broken on Chrome/macOS, (c) popup not closing after select. All 4 places (Admissions DOB, StudentDetail DOB edit, Fees payment date, Attendance class date) now use [`<DatePicker>`](../frontend/src/components/ui/date-picker.tsx) — popover-based with year/month dropdowns, auto-closes on selection, accepts `min`/`max` ISO strings. Built on `@radix-ui/react-popover` + `react-day-picker@9` + `date-fns`. **For any new date input: import `DatePicker` from `@/components/ui/date-picker`, never re-introduce `<Input type="date">`.**

4. **Vite ships everything in `frontend/public/` verbatim into `dist/` — except APKs, which each deploy publishes for its own env.** `frontend/public/downloads/` holds BOTH flavors' gitignored build outputs (`kis-attendance.apk` prod, `kis-attendance-test.apk` staging, plus both manifests), so shipping `dist/downloads/` as-is used to put the prod APK on TEST, and the `rsync --delete` wiped a server's APK whenever the local copy was missing. Since 2026-10-19 `push_frontend` excludes `downloads/` and `push_downloads` publishes only `$APK_LOCAL_NAME` as `downloads/kis-attendance.apk` + `$MANIFEST_NAME` (from env.sh), never deleting anything. Other static assets under `public/` still ship verbatim (and are still subject to `--delete`).

5. **`Theme.Material3.*` XML themes need `com.google.android.material:material`.** AGP doesn't include the Google Material Components library by default — only Compose Material 3 (which is a runtime-only Kotlin library, no XML resources). When the manifest references `Theme.Material3.DayNight.NoActionBar` for the Activity, AAPT errors with "resource style not found" unless you add `implementation("com.google.android.material:material:1.12.0")` to [android/app/build.gradle.kts](../android/app/build.gradle.kts). Adds ~700 KB but is the standard pattern for any Compose app that uses an XML theme parent.

6. **`rememberScrollState()` is itself `@Composable` — don't wrap it in `remember{}`.** Compose has two flavors of remember: composable factories like `rememberScrollState()`, `rememberCoroutineScope()`, `rememberDatePickerState()` already memoize their result. Wrapping them in another `remember { ... }` (whose lambda is non-composable) gives "Composable invocations can only happen from the context of a @Composable function." Just call them directly: `val scroll = rememberScrollState()`, not `val scroll = remember { rememberScrollState() }`.

7. **Android version is single-source-of-truth at [android/version.properties](../android/version.properties).** Both `versionCode` and `versionName` live there; `app/build.gradle.kts` reads them at configure time. Don't hardcode versions in `defaultConfig {}`. `scripts/build-android.sh` auto-increments `versionCode` on every release build (commits the new value back to the file), so build numbers are monotonic and unique across machines without manual bookkeeping. **`versionName` stays manual** — edit `version.properties` directly when you want a user-visible bump (e.g. 1.0.0 → 1.1.0). The Login footer + Home → About dialog both read from `BuildConfig.VERSION_NAME` / `VERSION_CODE`, so they never drift from the actual APK metadata.

8. **SQLAlchemy `Enum(MyEnum)` persists Python attribute names by default — not the `.value`.** With a hyphenated MySQL ENUM column (`Enum("report-card", "pseb-admit-card")`) and a Python enum like `class TemplateKind(str, enum.Enum): pseb_admit_card = "pseb-admit-card"`, the default sends `"pseb_admit_card"` (attribute name with underscore) and MySQL replies `Data truncated for column 'kind'` (errno 1265). Fix: `Enum(TemplateKind, values_callable=lambda obj: [e.value for e in obj], native_enum=False, length=32)`. Lives in [backend/app/models/pdf_template.py](../backend/app/models/pdf_template.py).

9. **FastAPI router order matters when path-params can shadow specific routes.** The legacy `pdf` router has `POST /pdf/{kind}` (catch-all). Registering `pdf_templates` AFTER it makes `POST /pdf/templates` resolve to the catch-all with `kind="templates"` instead of the templates router. **Always register the more-specific router first.** [backend/app/main.py](../backend/app/main.py) registers `pdf_templates.router` and `pdf_templates.cache_router` BEFORE the `api_routers` loop that includes `pdf`.

10. **WeasyPrint `position: absolute; bottom: 0` collapses on short content.** When the body content is shorter than the page (e.g. a 3-line letter), the wrapper element is sized to its content and `bottom: 0` anchors the footer to wherever content ends — not to the A4 page bottom. Switch to `position: fixed; bottom: 0`: WeasyPrint treats fixed elements as "render on every page" and pins them to the printable-area bottom regardless of content. Add `padding-bottom: 42px` on the page wrapper so body content can't slide underneath. Verified across all 5 brand-frame docs: footer y_from_bottom 7–8pt (its own internal padding). Lives in [backend/app/pdf/templates/_base.html.j2](../backend/app/pdf/templates/_base.html.j2). Same trick used for the PSEB signatures block.

11. **KIS crest PNGs are 5:4 landscape (256×204 / 1024×816), not square.** Forcing `h-11 w-11` squashes them. Always `h-X w-auto` with the correct intrinsic `width`/`height` attrs (e.g. `width=70 height=56`). Used across [Login.tsx](../frontend/src/pages/Login.tsx), [header.njk](../public-site/src/_includes/header.njk), [_base.html.j2](../backend/app/pdf/templates/_base.html.j2). Same goes for any future logo asset — keep aspect ratio honest.

12. **`log.info("...", extra={"name": ...})` crashes with `KeyError: "Attempt to overwrite 'name' in LogRecord"`.** Python's `logging.LogRecord` reserves a long list of built-in attribute names — passing any of them via `extra=` raises a hard `KeyError` in `makeRecord` (logging/__init__.py:1656). **Reserved keys to avoid:** `name`, `msg`, `args`, `levelname`, `levelno`, `pathname`, `filename`, `module`, `exc_info`, `exc_text`, `stack_info`, `lineno`, `funcName`, `created`, `msecs`, `relativeCreated`, `thread`, `threadName`, `processName`, `process`, `message`. **In this repo:** rename to `student_name` / `staff_name` / `entity_name` etc. The crash bites *after* the DB commit, so requests fail with a 500 even though the write succeeded — silent data hazard. Caught and fixed in Session 9 students.py:167, staff.py, and the new soft-delete handlers.

13. **HTML `<input type="number">` spinner arrows + `Number(e.target.value) || N` fallback caused the "100 → 31" data-entry bug.** Teachers editing Max Marks could brush the up-arrow spin button, then type "3" → field jumps to "31" (or worse). Fixed app-wide in Session 13: (a) [components/ui/input.tsx](../frontend/src/components/ui/input.tsx) hides spinners globally via `[appearance:textfield] [&::-webkit-{inner,outer}-spin-button]:appearance-none`; (b) new [`NumberField`](../frontend/src/components/ui/number-field.tsx) stores state as `string` (empty allowed), enforces `max`/`min` by *rejecting* keystrokes that would exceed bounds (controlled input snaps back to last valid value). Use `NumberField` for any bounded numeric input; raw `<Input type="number">` is OK only for unbounded fields like display order or annual fee (kept on strings via `digitsOnly()`).

14. **MySQL UNIQUE(batch_id, student_id) plus nullable `batch_id` gives free upsert + legacy tolerance.** MySQL (unlike Postgres) treats NULL as distinct in unique indexes, so legacy `marks` rows with `batch_id IS NULL` never collide. New rows from `/marks/batches` always populate `batch_id`, so the unique constraint enforces upsert semantics: re-saving the same batch updates rows instead of duplicating. Lets you ship the batch workflow without backfilling 2 years of pre-existing marks. Same trick reusable for any "migrate to batched X" feature later. See [models/marks.py](../backend/app/models/marks.py) `__table_args__`.

15. **Vite cache-bust contract: embedded `__BUILD_ID__` + `dist/version.json` + runtime poll + nginx no-cache.** Hashed asset filenames bust themselves on rebuild, but cached `index.html` keeps referencing the OLD hashes — that's the "user needs hard refresh after deploy" loop. Session 13 fix in 4 parts: (a) [vite.config.ts](../frontend/vite.config.ts) generates a fresh `BUILD_ID` each build, injects it as `__BUILD_ID__` via `define`, and emits `dist/version.json` via a tiny plugin; (b) [lib/version.ts](../frontend/src/lib/version.ts) `useVersionCheck()` polls `version.json` with `cache: 'no-store'` every 5 min while visible and reloads with a `?_v=<ts>` query-bust on mismatch (the query bust is essential — `window.location.reload()` alone respects the cached HTML); (c) the nginx configs ([deploy/nginx.kisschool.conf](../deploy/nginx.kisschool.conf) PROD, [deploy/nginx.school-test.conf](../deploy/nginx.school-test.conf) TEST) add exact-match `location` blocks sending `Cache-Control: no-cache, must-revalidate` for `<base>/admin/`, `index.html`, and `version.json`; (d) `define: { __BUILD_ID__: JSON.stringify(...) }` — **must** use `JSON.stringify`, otherwise the substituted string is unquoted and the bundle fails to parse. To roll out a TEST snippet change: `(set -a; source scripts/deploy/test/env.sh; set +a; bash scripts/provision/06-install-nginx-snippet.sh)` — it re-renders, `nginx -t`s and reloads. PROD's vhost is installed by hand.

16. **Android R8/ProGuard keep rule must track the package name.** `app/proguard-rules.pro` keeps Gson DTOs by package: `-keep class in.kisschool.data.api.dto.** { *; }`. When the package was renamed `com.expressonly.kisattendance → in.kisschool`, the old keep rule matched nothing → R8 obfuscated DTO field names in the **release** build only → the app sent login as `{"<garbled>":…}` → backend `422` (and every API call broke). Debug builds (no minify) hid it. Fix: keep rule on the new package **plus** `-keepclassmembers,allowobfuscation class * { @com.google.gson.annotations.SerializedName <fields>; }`. Verify via `app/build/outputs/mapping/<flavor>Release/mapping.txt` — the DTO class should map to itself.

    **Refinement (Session 19):** anything persisted as JSON outside `data/api/dto` (e.g. the saved-accounts list in `data/auth/AccountStore.kt`) is renamed by R8 in release builds — store it with `org.json` and explicit keys, never Gson, or saved data vanishes after an app update. Per release: every `in.kisschool.data.api.dto.* -> ` line in `mapping.txt` must map to itself.

17. **`frontend/vite.config.js` is a committed `tsc` artifact and Vite prefers `.js` over `.ts`.** `npm run build` (= `tsc -b && vite build`) regenerates it from `vite.config.ts`, but a bare `npx vite build` uses the STALE `.js`. Base path is build-time parametrized: `vite.config.ts` reads `process.env.VITE_BASE ?? "/kisschool/admin/"`; `VITE_API_URL` is shell-exported (overrides `.env.production`); favicon uses a `%BASE_URL%` placeholder substituted by a `transformIndexHtml` plugin (a plain relative favicon 404s on SPA deep links). `scripts/deploy/<env>/env.sh` sets `VITE_BASE`/`VITE_API_URL`/`SITE_BASE_PATH`/`HEALTH_PATH`/`SITE_URL_PATH` (test → `/kisschool/...` on `http://69.62.72.137`, prod → root). **To typecheck without building, run `npx tsc -b`** — `npx tsc -b --noEmit` fails on this repo's project-references setup with `TS6310: Referenced project 'tsconfig.node.json' may not disable emit`. See [[feedback_vite_base_parametrization]].

18. **`GET /api/students` is paginated** (`{items,total,page,page_size}`) — clients must read `.items`. The Android app's bare-`List<StudentDto>` DTO silently broke against the live backend until fixed with a `StudentPageDto` wrapper. Also: `in` is a Kotlin hard keyword, so the `in.kisschool` package must be backtick-escaped (`` `in`.kisschool ``) in every `package`/`import` (Gradle `namespace`/`applicationId` strings don't); and AGP forbids a product-flavor name starting with `test` → the staging flavor is named `staging` with `applicationIdSuffix = ".test"`.

19. **Staff dual-credential temp password (migration 0010).** `staff.temp_password_hash` is a SECOND valid login that does NOT replace `password_hash` — admin/super-admin set it from the web Staff page to cover an absent teacher; login accepts real-OR-temp; a temp login never triggers force-password-change; cleared by admin (no auto-expiry). `POST/DELETE /api/staff/{id}/temp-password`. **Forgot-password (migration 0011)** works for admin/super-admin/staff (`_resolve_reset_account` maps the hardcoded admin emails); needs SMTP set in `.env` (`SMTP_*`, Zoho `info@kisschool.in`) + `APP_BASE_URL=https://kisschool.in/admin` so reset links are correct. The web ForgotPassword form must POST `{identifier}` (not `{email}`).

20. **A cache key must cover EVERY input, not just the versioned one.** `pdf_cache` was keyed on `(kind, student_id, template_id, template_version)` — but a report card is also rendered from the `marks` table and `pdf_student_data`, and editing those does **not** bump `template.version`. Result: correct a student's marks, re-render, and the API happily serves the stale cached PDF. Fix (migration 0013): `pdf_cache.source_hash` = sha1 of the sorted `subject|exam_type|marks|max_marks` tuples plus the JSON-sorted student data; the lookup matches on it alongside the version, so any marks edit misses and re-renders. Consequence for the code shape: `render_or_cache` must now **gather its render inputs BEFORE the cache lookup** (the hash needs them), which inverts the old "check cache first, load nothing on a hit" ordering — a hit now costs two cheap SELECTs. Existing rows have `source_hash IS NULL` and miss exactly once. **General rule for this repo: before caching a derived artifact, enumerate every table it reads and make sure each one is either in the key or hashed into it.**

    **Refinement (Session 19):** report cards now hash the final template payload (`services/report_cards.payload_hash`) together with `REPORT_CARD_TEMPLATE_REVISION` and `RESULTS_ENGINE_VERSION` — bump the template revision whenever `report-card.html.j2` changes (it is 4 after the photo/spacing fix, Gotcha #24), or cached cards keep the old look.

21. **"Every class" is stored as a single literal sentinel row `class_name="All"`, so every consumer must expand it.** `staff_classes` holds one row with the string `"All"` rather than 15 rows (the staff bulk-import writes it; the frontend collapses a full selection back to `["All"]`). That literal leaked into the JWT `allowed_classes` claim and out through `GET /api/auth/me`, so the Android app and the web class pickers rendered a bogus "All" option, and `assert_class_allowed` rejected every *real* class name for those users. Fix: [backend/app/constants.py](../backend/app/constants.py) owns the canonical `CLASSES` list (mirrors `CLASSES` in [frontend/src/lib/utils.ts](../frontend/src/lib/utils.ts) and the Android list — **keep all three in sync**) plus `expand_classes` / `is_all_sentinel`. Expansion happens in **two** places on purpose: at login before the token is minted, and again in `deps._parse` on decode — the second one is what repairs tokens issued before the fix, which stay valid for up to 8h. `assert_class_allowed` also short-circuits on the sentinel as a belt-and-braces guard. **If you add a third client that reads `allowed_classes`, it gets concrete names — never special-case the string `"All"` again.**

    **Refinement (Session 19):** admins and the super-admin carry an EMPTY `allowed_classes`, so clients must use the all-classes rule (`AuthRepository.visibleClasses` on Android, `isAdmin ? CLASSES : allowed_classes` on the web), never the raw list — Take attendance / Past attendance / Students showed "No classes assigned" for admins. Server side, list endpoints use `deps.classes_in_scope(user)`: the old `if user.role == "staff" and user.allowed_classes:` filter let a teacher with NO classes see every class's attendance totals and every student.

22. **No AI attribution on commits or PRs — enforced in three layers, because settings alone cannot do it.** `attribution: {commit:"", pr:"", sessionUrl:false}` in `~/.claude/settings.json` *and* [.claude/settings.json](./settings.json) stops Claude Code's **automatic** trailer — but it does not stop an agent that types `Co-Authored-By:` into a commit message itself when some prompt tells it to (exactly what happened in Session 18). So:
    - **[.githooks/no-ai-attribution.sh](../.githooks/no-ai-attribution.sh)** — the single place the rule lives. Reads text on stdin, exit 1 if it finds an AI co-author/assisted-by trailer, a "generated with <AI>" line, a bot address like `noreply@anthropic.com`, or a `Claude-Session:` trailer. Extend the `AI_NAMES` alternation to cover a new model. `strict` mode anchors to line start (commit messages); `loose` also matches mid-line (one-line `git commit -m`) and **fails closed** — a commit message that merely quotes a trailer is rejected too, on purpose.
    - **[.githooks/commit-msg](../.githooks/commit-msg)** — the real backstop. Fires on commit / amend / merge / rebase / cherry-pick / squash, whoever drives it (agent, IDE, you). **Needs `git config core.hooksPath .githooks` once per clone** — `core.hooksPath` is local config and is NOT committed, so a fresh clone has no enforcement until you run it.
    - **`PreToolUse` Bash hook** in [.claude/settings.json](./settings.json), filtered by `if: "Bash(git commit *)"` / `"Bash(gh pr *)"` — fails fast with the reason before the command runs, and is the only layer that covers a `gh pr create --body`, which git hooks never see.
    - Escape hatch is `git commit --no-verify` (git skips all hooks); that's git's design, not a hole worth closing. Verified end-to-end: a real commit carrying the trailer is rejected with HEAD unchanged, the same message clean commits fine.

23. **Two instances on one box: every server resource is an env.sh knob.** Since 2026-10-19 PROD (`/opt/school-management`, user `school`, unit `school-management`, :8000, DB/user `school_management`/`school`) and TEST (`/opt/school-management-test`, `school-test`, `school-management-test`, :8001, `school_management_test`/`school_test`) share 69.62.72.137. `scripts/deploy/<env>/env.sh` is the only place those values live; `lib.sh` hands them to its quoted `<<'REMOTE'` heredocs as env assignments (`$(remote_env) bash -s`), and the `deploy/` templates use `__TOKEN__` placeholders rendered by `render_template` — never `envsubst`, which would blank nginx's `$host`/`$uri`. Rendering the unit with prod values is byte-identical to the live prod unit (checked by diff). Traps found on the way:
    - **`mysqldump` as an app user needs `--no-tablespaces`** — MySQL 8 wants PROCESS for tablespace metadata; without the flag the dump still completes but prints an access-denied error.
    - **TEST's nginx lives inside someone else's server block** (the enamfoss bare-IP :80 vhost): our prefix locations use `^~` so a future host regex can't hijack them; the host's `error_page 500 502 503 504 /50x.html` (file missing) turned "backend down" into a 404 until the API location declared its own `error_page` → JSON 503; locations with their own `add_header` re-declare the host's security headers. Step 06 inserts exactly one `include` line (backup in `/etc/nginx/backups/`, restored automatically if `nginx -t` fails).
    - **Step 03 refuses to `ALTER USER` a MySQL user this instance didn't create** — with two instances, resetting a shared user's password would break the other one.
    - **Deploying committed code from a dirty tree:** `SRC_ROOT=$(mktemp -d) && git archive HEAD backend frontend packages | tar -x -C "$SRC_ROOT"` — `packages/` is required because the frontend imports `packages/design-system` (i18n JSON, tokens.css, crest).
    - **Plain-HTTP TEST:** the staging Android flavor needs `android/app/src/staging/res/xml/network_security_config.xml` (cleartext for `69.62.72.137` only). Resource shrinking renames it inside the APK (e.g. `res/8G.xml`), so verify by content, not path. Browsers also block `navigator.clipboard` on HTTP origins, and Chrome warns on HTTP APK downloads.

---
    - **Deploying the working copy** (deploy → test → commit) without touching the repo: `SRC_ROOT=$(mktemp -d) && rsync -a --exclude node_modules --exclude dist --exclude .venv --exclude __pycache__ --exclude '*.tsbuildinfo' --exclude 'public/downloads' backend frontend packages "$SRC_ROOT/" && SRC_ROOT=$SRC_ROOT bash scripts/deploy/test/deploy-all.sh`. Every deploy re-publishes the repo's `frontend/public/downloads/<env APK>` + manifest, so build a new APK *after* deploying. TEST-only `.env` knob: `AUTH_COOKIE_PATH=/kisschool/api/auth` (Gotcha #25).

24. **WeasyPrint (63.x) ignores flex `gap`, and a `width/height: 100%` image inside a flex box collapses to nothing.** The report card's student photo never printed and the tiles, logo and grading scale touched their neighbours. Fix (Session 19, template revision 4): space flex children with margins (`.row > * + * { margin-left: … }`) and give images explicit pixel sizes (`display:block; width:74px; height:92px; object-fit:cover`). Check a rendered PDF with `pdfimages -list` (the photo must be listed). Locally WeasyPrint only finds Homebrew's Pango with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` — skill `sample-report-cards` renders made-up sample cards with the real code.

25. **Stay signed in (device sessions, migration 0021).** Access JWTs stay 1 hour (`JWT_EXPIRY_HOURS=1`); refresh tokens live 30 days sliding / 180 days absolute in `device_sessions` (sha256-hashed). Every `/auth/refresh` **rotates** the token, and presenting an already-rotated token revokes its whole family (replay) — except within 60 s while its successor is still unused (a lost response). So clients must (a) persist the new refresh token before using the new access token and (b) single-flight refreshes (web: one shared promise in `lib/api.ts` + a bootstrap gate in `App.tsx`; Android: OkHttp `Authenticator` with a lock). The web gets an HttpOnly `SameSite=Strict` cookie whose `Path` must equal the browser path of `/auth`: default `/api/auth` (prod), **TEST `.env` sets `AUTH_COOKIE_PATH=/kisschool/api/auth`** — otherwise the browser never sends it. Password change/reset, temp-password clear and staff deletion revoke sessions (`services/device_sessions.revoke_sessions_hook`, never raises). SSE/inline URLs carry the 1-hour token as `?token=`, so EventSources are recreated when it changes. Android unlock = `BiometricPrompt` with `BIOMETRIC_WEAK | DEVICE_CREDENTIAL` (face unlock on most phones is class 2), no CryptoObject; `MainActivity` must be a `FragmentActivity`.

## Status
| Area | Status |
|---|---|
| Core platform: FastAPI routers, SQLAlchemy 2 + Alembic, JWT + bcrypt, SSE broker, React SPA (top-bar/sidebar nav, DatePicker, NumberField, bulk CSV import, validation, auto cache-bust) | ✅ Sessions 3–13 (Gotchas #13, #15) |
| Deploy framework (snapshot + auto-rollback, slash commands, idempotent provisioning; two instances on one box) | ✅ (Gotcha #23) |
| PROD https://kisschool.in | ✅ live on `339c013`, schema **0021** (deployed 2026-10-20 11:33 after a 62 MB backup), Android prod **v1.3.4 build 25** (force-update armed); 11th/12th Mathematics optional, no takers ticked |
| TEST http://69.62.72.137/kisschool/admin/ | ✅ dev `339c013`, schema **0021**, staging app **v1.3.3 build 24**; prod-clone data (synced 2026-10-19) |
| Class-templated PDFs + cache, soft-delete workflow, staff auth (email/phone, temp + forgot password), class-subjects master, marks draft/lock workflow | ✅ Sessions 8–16 |
| Term-scoped results engine + "All" class sentinel | ✅ on prod (0013) (Gotchas #20, #21) |
| **Results module v2** — sessions, letter grades, rank/attendance, report card v2 (layouts, overrides, photo), background renders + ZIP, revision guard, cross-check fixes | ✅ on TEST (0014–0019) |
| **Optional subjects** (11th/12th Mathematics) | ✅ on TEST (0020); real takers not ticked yet |
| **Role dashboards + brand look** (web pie + class-wise chart; Android drawer, module colours, theme option, Notices) | ✅ on TEST |
| **Stay signed in** (device sessions, web Remember me, Android fingerprint/face + saved accounts) | ✅ on TEST (0021) — phone check of the biometric flow pending |
| Android teacher app `in.kisschool` (flavors, force-update gate, attendance incl. half day/holiday, approvals, marks entry, results/report cards) | ✅ (Gotchas #2, #7, #16, #18) |
| iOS scaffold | 🟡 builds in Xcode only; far behind Android; needs the Apple Developer Program |
| Bilingual portal (Sprint 4) | 🟡 new pages bilingual; older page labels and every Android string English-only |

## Slash Commands (mirror uploadmytds)
| Command | Script | Purpose |
|---|---|---|
| `/provision-test` | `scripts/provision/provision.sh` | One-time TEST-instance bootstrap on the prod box (idempotent: prereqs / `school-test` user / dirs / MySQL DB+user / .env / systemd unit / nginx snippet included from the enamfoss vhost) |
| `/deploy-test` | `scripts/deploy/test/deploy-backend.sh` | Backend-only deploy to TEST |
| `/deploy-test-frontend` | `scripts/deploy/test/deploy-frontend.sh` | Frontend-only (Vite build + rsync) |
| `/deploy-test-all` | `scripts/deploy/test/deploy-all.sh` | Backend + frontend with snapshot + auto-rollback |
| `/sync-test-data` | `scripts/deploy/test/sync-from-prod.sh` | Replace the TEST DB with a fresh prod clone (same box), migrate to TEST's code, restart. Destructive for TEST only |
| `/deploy-prod` `/deploy-prod-frontend` `/deploy-prod-all` | `scripts/deploy/prod/*.sh` | PROD versions; require typing `DEPLOY PROD` to confirm. PROD `env.sh` must have CHANGE_ME placeholders replaced first. |
| `/clean-logs` | local `rm -rf logs_backup_*` | Clean local log-backup dirs (after explicit y) |
| `/release-android` | `scripts/build-android.sh {prod\|test}` + `scripts/deploy/<env>/upload-apk.sh` (gated by `y/N`) | Build a fresh signed APK for a flavor, then ask before uploading just the APK + manifest to that env (verifies HTTP 200 + byte size before arming the manifest). Skips the SPA rebuild |
| `/check-logs` | `scripts/deploy/test/check-logs.sh` (also `prod/`) | Read-only log analysis: 6 sections (service status / journalctl / error.log tail / recent tracebacks / access.log tail / 4xx-5xx). Accepts `30m`, `2h`, `1d`. Nothing written, nothing downloaded — single SSH session straight to terminal |
| `/save-session` | [commands/save-session.md](./commands/save-session.md) | Snapshot session context to `.claude/CLAUDE.md` + `SESSION_HISTORY_*`/`GOTCHAS_*` archives + `.claude/memory/`. Prompt-library v2026-08-31; the `## Project-Specific Notes` block (P1–P6) in that file is this project's local override set — preserved across prompt-library updates |
| `/deep-analysis` | [commands/deep-analysis.md](./commands/deep-analysis.md) | Generate a multi-document onboarding knowledge base at `.claude/doc/deep-analysis/` (README + 00–10). Prompt-library v2026-08-31; `## Project-Specific Notes` (P1–P3) pre-fills the KIS domain context and the "verify CLAUDE.md against code" rule |
| `test-verification` *(skill)* | [skills/test-verification/SKILL.md](./skills/test-verification/SKILL.md) | Verify a TEST deploy: on-box smoke (26 checks), API checks (results, dashboards, stay-signed-in) and headless-Chrome browser checks — logins from env vars only |
| `sample-report-cards` *(skill)* | [skills/sample-report-cards/SKILL.md](./skills/sample-report-cards/SKILL.md) | Render sample report-card PNGs from a made-up class with the real code (local WeasyPrint) for design reviews |
| `kis-design-system` *(skill)* | [skills/kis-design-system/SKILL.md](./skills/kis-design-system/SKILL.md) | Brand tokens, i18n and Punjabi rules for any UI/copy edit (portal, public site, PDFs, Android) |

**Fresh-clone setup:** `git config core.hooksPath .githooks` (arms the no-AI-attribution commit hook — Gotcha #22; local config, not carried by clone).

Other manual scripts: `scripts/deploy/test/download-logs.sh` · `backup-db.sh` · `rollback.sh <timestamp>`. Same set under `scripts/deploy/prod/`. Plus `scripts/build-android.sh` (release APK build + copy to `frontend/public/downloads/`).

## Server-side Layout (69.62.72.137 — two instances + the enamfoss Tomcat app)
```
/opt/school-management/            PROD  (755, school)          unit school-management       gunicorn 127.0.0.1:8000  DB school_management / school
/opt/school-management-test/       TEST  (755, school-test)     unit school-management-test  gunicorn 127.0.0.1:8001  DB school_management_test / school_test
  ├── app/ (+ .venv/)   frontend/dist/ (downloads/ = this env's APK + manifest)   logs/   backups/ (TEST 700)
  └── .env (600)   .my.cnf (600)   .db_password (600 root)
  (PROD also has public-site/dist/)

/etc/nginx/conf.d/kisschool.conf                 PROD vhost (kisschool.in :80→:443, root layout)
/etc/nginx/conf.d/enamfoss.conf                  enamfoss bare-IP :80 vhost — NOT ours, except ONE line:
                                                 include /etc/nginx/snippets/school-management-test.conf;
/etc/nginx/snippets/school-management-test.conf  TEST routes /kisschool/{api,admin,downloads}/
/etc/nginx/backups/                              step-06 backups of edited nginx files
```

## Next Steps (TODOs)
0. **Watch prod after the 2026-10-20 go-live:** `/check-logs` (prod) over the next days (its "last 3 tracebacks" are not time-filtered — the May `notify_student_edit_request` NameError still shows; compare timestamps); teachers will be forced onto app 1.3.4 the next time they open it. Rollback if needed: code snapshot `20261020_113317` via `scripts/deploy/prod/rollback.sh`, DB backup `~/Downloads/db-backups/school_prod_20261020_113300.sql.gz` (migrations 0014–0021 are additive; 0019 cleared 2 empty v1 card rows).
1. **Tick the real Mathematics takers** in 11th and 12th on prod (Class Subjects → Mathematics) — until then nobody can enter Mathematics marks there ("No student takes this subject yet").
2. **Owner's phone checks (prod app 1.3.4 / TEST 1.3.3):** "Sign in faster" popup → fingerprint/face unlock after reopening, Switch account between super-admin/admin/teacher, Settings (App lock, signed-in devices), dark theme, both role dashboards (pie → Pending/Marked lists).
3. **Fees:** staff #4 holds the Fees menu — can list fees (fixed 2026-10-20, `339c013`) but recording/deleting payments stays admin-only, as before; decide whether Fees-menu holders should record payments too.
4. **Awaiting the principal:** renaming mistyped exam names in 11th/12th English ("PT First" → "P.T. First", "P.T Second" → "P.T. Second") — do NOT apply, not even on TEST. Also raise: only 6 of 15 classes marked attendance in October 2026; 4 marks batches are still drafts (left off report cards until submitted).
5. **Auth follow-ups:** nginx `limit_req` on `/api/auth/login` + `/api/auth/refresh` in both vhosts (prod vhost is hand-installed); `AUTH_COOKIE_PATH` into `deploy/.env.example` + provision step 04 (peer-owned scripts — coordinate); once every phone is on 1.3.x, shorten `JWT_EXPIRY_HOURS` to 15–30 min; a web page for signed-in devices and the admin "sign out a lost phone" action (API exists).
6. **Verify the seeded exam pattern** for 9th–10th (some values ambiguous against the handwritten sheet) — super-admin spot-check on `/class-subjects/:id`.
7. **Roadmap first five** ([docs/ROADMAP.md](../docs/ROADMAP.md)): nightly off-box backups (none exist today) · fee structure + dues ledger · WhatsApp/SMS notices · offline-first attendance · session-end promotion workflow (before March 2027). Deferred small items are listed there too.
8. **Bilingual polish:** older portal pages (Students/Attendance/Fees/Staff/Reports) and all Android strings (none are in resources; add `values-pa`).
9. **Sprint 6** — STATUS.md + Lighthouse + axe report.
10. **iOS** has none of Sessions 14–19; Apple Developer Program ($99/yr) gates distribution.
11. **Code-split the frontend** (bundle ≈ 1.4 MB) — lazy-load reports/templates/class-subjects routes.
12. Downscale the Android document-photo upload (web compresses to ~900 px JPEG; the app uploads the original).
13. Optional later: Redis pub/sub for SSE if the instance runs more than one worker process for live updates; structured JSON logging.

## Session History

> Sessions 1–2 (Firebase era) archived → [SESSION_HISTORY_1_2.md](./SESSION_HISTORY_1_2.md)
> Session 3 (FastAPI/MySQL migration scaffold) → [SESSION_HISTORY_3.md](./SESSION_HISTORY_3.md)
> Session 4 (Production deploy + reusable infra) → [SESSION_HISTORY_4.md](./SESSION_HISTORY_4.md)
> Session 5 (UX hardening + bulk import) → [SESSION_HISTORY_5.md](./SESSION_HISTORY_5.md)
> Session 6 (Android app + web date pickers) → [SESSION_HISTORY_6.md](./SESSION_HISTORY_6.md)
> Session 7 (iOS app scaffold + Mobile Apps page) → [SESSION_HISTORY_7.md](./SESSION_HISTORY_7.md)
> Sessions 8 (KIS design + templated PDFs) + 9 (soft-delete workflow + /check-logs) → [SESSION_HISTORY_8_9.md](./SESSION_HISTORY_8_9.md)
> Session 10 (staff email/phone+password auth) + 11 (useBlocker fix) — see memory `project_staff_auth_revamp` / `feedback_useblocker_data_router`
> Session 12 (top-bar nav) → [SESSION_HISTORY_12.md](./SESSION_HISTORY_12.md)
> Session 13 (Class Subjects master + marks draft/submit/lock/edit-request workflow + auto cache-bust) → [SESSION_HISTORY_13.md](./SESSION_HISTORY_13.md)
> Session 14 (Android force-update gate) + 15 (Android dashboard + back-dated attendance, v1.2.3) + 17 (attendance half-day/holiday/clear-day + in-app approvals portal, v1.2.4) — see memory `project_android_force_update` / `project_android_dashboard_attendance`
> Session 16 (PROD launch at kisschool.in + `in.kisschool` rebrand + temp/forgot password; historical promote-to-prod steps) → [SESSION_HISTORY_16.md](./SESSION_HISTORY_16.md)
> Session 18 (term-scoped results engine + "All" sentinel) → [SESSION_HISTORY_18.md](./SESSION_HISTORY_18.md) · Session 19 full detail → [SESSION_HISTORY_19.md](./SESSION_HISTORY_19.md)

### Sessions 18–19 — 2026-10-18 → 2026-10-19 · Results module v2, end to end (on TEST)

**Branch:** `dev` · prod untouched (`54db9cd`, schema 0013) · TEST = dev `a71d7b7`.
- **Session 18:** one pure engine (`services/results.py`) for the results table and the report card, component `term` (0013), marks-aware PDF cache (Gotcha #20), "All" class-sentinel expansion (Gotcha #21) — live on prod.
- **Session 19 (plan phases 0–6):** academic sessions (0014), letter grades (0015), report card v2 with `summary`/`components` layouts and computed rank/attendance (0016), background render jobs + ZIP (0017). A 58-item cross-check added the batch **revision** guard (0018: stale screen → 409; app builds 19/20 can't remove saved marks), cleared v1 card overrides (0019), integer-only marks, grades null until complete, `includeDrafts` super-admin-only, Force re-render admin-only.
- **Optional subjects** (0020) for 11th/12th Mathematics: `not_taken` for non-takers, never blocks promotion, rank by exact %; on TEST both are optional with no takers ticked.
- From the principal's sample review: photos now print and flex spacing works (Gotcha #24). Results opens on Term 1 while Term 2 is empty. Policy confirmed — memory `project_results_policy`; exam-name renames still await the principal.
- Verified on TEST: pytest ✓, smoke 26/26, optional 12/12, browser checks as super-admin/admin/teacher (skill `test-verification`).

### Session 19 — 2026-10-19 · Role dashboards, brand look, app theme

**Branch:** `dev` · on TEST · commits `8fb38a7` (server) · `3ef6c60` (web) · `63e10d8`/`134d271`/`af44687`/`1ffe380` (app) · `4ad7e96` (roadmap).
- Server: `GET /attendance/class-summary` and `GET /marks/batches/summary`; scope holes closed (Gotcha #21: teachers with no classes, unscoped `GET /fees`); attendance CSV onto a holiday clears the flag.
- Web dashboard: admin marked/pending/holiday classes pie → class lists; class-wise attendance chart for every role (Today/Week/Month, ≥ 90 / 75–89 / < 75 bands, 75 % PSEB line).
- Android: admins see every class; ☰ drawer; admin and teacher dashboards (classes pie → `classes-today/{kind}` lists, donut, class-wise bars, approvals/session, marks progress, fees, notices…); module colours (`KisModule`), gradient headers, Playfair Display Bold, `KisIcons`, Notices; theme Light (default) / Dark / Same as phone with a readable dark palette.
- [docs/ROADMAP.md](../docs/ROADMAP.md): ~25 future features, the first five, deferred items.

### Session 19 — 2026-10-19 · Stay signed in (device sessions, web Remember me, fingerprint/face app sign-in)

**Branch:** `dev` · on TEST (0021) · commits `b211a3e` (server) · `c686312` (web) · `6916304` + `a71d7b7` (app 1.3.3 build 24).
- Cause: 1-hour JWTs and no server session state → the password every hour, app and web.
- Server: `device_sessions`, rotating refresh tokens (replay → family revoked; 60-s lost-response grace), `/auth/refresh`, `/auth/logout`, `/auth/sessions`, admin lost-phone revoke, revocation on password change/reset, temp-password clear and staff deletion, 429 after 10 failed logins; 32 tests. Rules: Gotcha #25.
- Web: Remember me → HttpOnly cookie; bootstrap + single-flight refresh; SSE reconnects with the new token; Logout ends the server session.
- Android: "Sign in faster next time?" → App lock (fingerprint, face or phone PIN) on open and after 15 min away; several saved accounts, Switch account, Settings (theme, App lock, signed-in devices); new deps biometric/fragment-ktx/lifecycle-process.
- Verified on TEST: 11 API + 5 browser checks. **Biometric flow not yet run on a phone (owner).**

## Active MCP Servers
None configured (no `.mcp.json`).

## Active Hooks
`.claude/settings.json` → `PreToolUse` on Bash, filtered `Bash(git commit *)` and `Bash(gh pr *)`: pipes the command through `.githooks/no-ai-attribution.sh loose` and blocks it on an AI attribution trailer (Gotcha #22). The git `commit-msg` hook in `.githooks/` is the backstop (`git config core.hooksPath .githooks` once per clone).

## Active Subagents
None configured (no `.claude/agents/`). Multi-agent work uses ad-hoc Workflow scripts — pacing rules in memory `feedback_usage_pacing`.

## Documentation
- Old single-file Firebase app (read-only reference): [_archive/index.firebase.html](../_archive/index.firebase.html)
- Bootstrap → Tailwind migration handled inside the React rewrite
- shadcn/ui: https://ui.shadcn.com/
- TanStack Query: https://tanstack.com/query/v5
- FastAPI: https://fastapi.tiangolo.com/
- Alembic: https://alembic.sqlalchemy.org/
- Architecture plan: [/Users/manjeetsaini/.claude/plans/create-a-deep-plan-snug-tome.md](/Users/manjeetsaini/.claude/plans/create-a-deep-plan-snug-tome.md)
- Future work (not scheduled): [docs/ROADMAP.md](../docs/ROADMAP.md) · session archives: `.claude/SESSION_HISTORY_*.md`, `.claude/GOTCHAS_*.md`

> Context usage guide: 0–60% work freely | 60–70% monitor usage | 70–80% run /compact | 80%+ run /clear (mandatory)
