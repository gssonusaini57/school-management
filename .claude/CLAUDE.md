# Project Memory
**Last Updated:** 2026-06-06 | **Sessions:** 16 (1–12 archived) | **Branch:** dev | **Stage:** ✅ **LIVE ON PROD** at https://kisschool.in (served at the domain ROOT) **and** TEST at https://expressonly.in/school/. Android teacher app rebranded to package **`in.kisschool`** with prod/staging flavors + force-update gate. Session 16 added: prod launch + base-path parametrization, staff **temporary-password** (admin override), **forgot/reset-password** (Zoho email), and app **Edit-Student / Marks-Entry / document-upload** screens.
> **Admin logins (both servers):** admin `nsnishasaini57@gmail.com / admin123` · super-admin `gssonusaini57@gmail.com / <changed — not super123>`. Staff log in by email-or-phone + password. Test & prod share identical admin/super-admin password hashes + SMTP creds.

> Slash commands: see [.claude/commands/](./commands/) — `/provision-test`, `/deploy-test*`, `/deploy-prod*` (incl. `/deploy-prod-public-site`), `/clean-logs`, `/check-logs`, `/release-android`, `/save-session`. Android APK build: `bash scripts/build-android.sh {prod|test}` (local, needs keystore).

---

## Design system (KIS brand handoff — Session 8 shipped)

Handoff package at [_handoff/khalsa-international-handoff/](../_handoff/khalsa-international-handoff/). Tokens / fonts / bilingual i18n / brand SVGs mirrored at [packages/design-system/](../packages/design-system/). The React portal, the static public site at `public-site/`, and the WeasyPrint PDF templates all share the same palette and fonts (Playfair Display · Cinzel · Cormorant Garamond · Manrope · Noto Sans Gurmukhi).

**For implementation rules (tokens / i18n / currency-date / Punjabi-fallback) read the skill at [.claude/skills/kis-design-system/SKILL.md](./skills/kis-design-system/SKILL.md) before editing any UI or copy.**

**Surfaces (delivered):**
- Public marketing site → static HTML via Eleventy + Tailwind CLI in `public-site/`, deployed to nginx at `/school/`. (Separate from the React app.)
- Staff portal at `/school/admin/` → retrofitted to KIS palette + bilingual scaffolding.
- Print PDFs → Python WeasyPrint pipeline in `backend/app/pdf/`. **Sprint 5 polished + shipped Session 8**: 6 doc kinds (letterhead-a/b, fee-receipt, salary-slip, report-card, pseb-admit-card) with shared brand frame (tri-band, Cinzel motto footer, watermark crest). Footer pinned via `position: fixed` (Gotcha #14).
- **NEW Session 8: class-templated bulk PDF flow** for `report-card` and `pseb-admit-card` — admin saves per-class config once, fills per-student data in a spreadsheet, bulk-renders with server-side cache keyed on `(kind, student_id, template_id, template_version)`. Editing a template bumps the version and auto-invalidates the cache.
- Parent mobile app — **still deferred**.

**Migration status (Sprint 1 = foundation, Sprint 6 = final report):**

| Track | Status |
|---|---|
| Sprint 1 — `packages/design-system/`, fonts, i18n libs in portal | ✅ shipped |
| Sprint 2 — Restyle React portal shadcn primitives to KIS tokens | ✅ shipped |
| Sprint 3 — Static public site (Eleventy, en+pa, 9 pages) | ✅ shipped |
| Sprint 4 — Bilingual the staff portal (en+pa across 12 pages) | 🟡 partial — login + sidebar + new Templates page bilingual; per-page table headers + form labels TODO |
| Sprint 5 — Print PDF templates (WeasyPrint, 6 templates) | ✅ shipped |
| Sprint 6 — STATUS.md + Lighthouse + axe report | ❌ pending |
| **Sprint 7 (new)** — Class-templated bulk PDF flow with cache | ✅ shipped Session 8 |

Active plan file: `/Users/manjeetsaini/.claude/plans/reactive-chasing-crab.md` (currently holds Sprint 7 — the templated-PDF spec).

---

## Project Overview
**KIS School Management Portal** — Internal web app for KIS (a single school).
Used daily by administrators and teachers to manage students, attendance, marks, fees, notices, and staff.

**Status (post-migration scaffold):** Firebase fully ripped out. New stack:
- **Backend:** FastAPI + MySQL (test VPS reuses uploadmytds's MySQL instance)
- **Frontend:** React + Vite + TypeScript + Tailwind + shadcn/ui
- **Realtime:** Server-Sent Events (no Firebase listeners)
- **Auth:** JWT with bcrypt-hashed credentials (admin password + staff access codes)
- **Hosting target:** `https://expressonly.in/school/` on test VPS `104.237.5.113`
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
| Database | MySQL 8.0 (shared with uploadmytds; new schema `school_management`) |
| File storage | MySQL `LONGBLOB` rows (no filesystem, no S3) |
| Auth | JWT (PyJWT, HS256, 8h) + bcrypt (passlib) for admin password & staff access codes |
| Hosting | Single VPS (test): nginx + systemd unit `school-management` |

---

## Repo Layout
```
school-management/
├── backend/                      # FastAPI app
│   ├── app/
│   │   ├── main.py               # FastAPI entry, mounts /api/* routers
│   │   ├── config.py             # pydantic-settings .env loader
│   │   ├── db.py                 # SQLAlchemy engine + session factory
│   │   ├── security.py           # bcrypt + JWT helpers
│   │   ├── deps.py               # current_user / require_admin / class scope
│   │   ├── events.py             # in-process pub/sub broker for SSE
│   │   ├── models/               # SQLAlchemy ORM (admin/staff/student/document/attendance/marks/fee/notice)
│   │   ├── schemas/              # Pydantic request/response models
│   │   └── routers/              # auth, students, files, attendance, marks, fees, notices, staff, reports, stream, health
│   ├── alembic/versions/         # Migrations (0001_initial.py = baseline)
│   ├── alembic.ini, alembic/env.py
│   ├── requirements.txt          # FastAPI, SQLAlchemy, Alembic, PyJWT, passlib, sse-starlette, etc.
│   └── pyproject.toml
├── frontend/                     # React SPA
│   ├── src/
│   │   ├── main.tsx              # QueryClient + BrowserRouter
│   │   ├── App.tsx               # Routes (Login + protected Layout)
│   │   ├── components/
│   │   │   ├── Layout.tsx        # Sidebar + topbar
│   │   │   ├── ProtectedRoute.tsx
│   │   │   ├── ChangePasswordDialog.tsx
│   │   │   └── ui/               # shadcn primitives
│   │   ├── pages/
│   │   │   ├── Login, Dashboard, Admissions, Students, StudentDetail
│   │   │   ├── Attendance, MarksEntry, MarksResults, Fees
│   │   │   └── Notices, Staff, Reports
│   │   ├── lib/
│   │   │   ├── api.ts            # axios instance + Bearer + 401 redirect
│   │   │   ├── auth.ts           # token + user helpers (useAuth hook)
│   │   │   ├── sse.ts            # useSSE(channel, invalidationKeys)
│   │   │   ├── compress.ts       # client-side image compression (900px JPEG q=0.75)
│   │   │   └── utils.ts          # cn(), CLASSES, COLORS, formatDate, formatCurrency
│   │   ├── types/api.ts          # mirrors backend Pydantic schemas
│   │   └── styles/globals.css    # Tailwind base + CSS vars
│   ├── vite.config.ts            # base "/school/", dev proxy /api → :8000
│   ├── tailwind.config.ts
│   ├── tsconfig.json             # path alias @/* → src/*
│   ├── .env.production           # VITE_API_URL=/school/api
│   ├── .env.development          # VITE_API_URL=/api
│   └── package.json
├── ios/                          # Native SwiftUI teacher app (Session 7) — XcodeGen-driven, .xcodeproj NOT committed
│   ├── project.yml                    # XcodeGen single source of truth
│   ├── version.xcconfig               # MARKETING_VERSION + CURRENT_PROJECT_VERSION
│   ├── KisAttendance/
│   │   ├── App/KisAttendanceApp.swift
│   │   ├── Data/{ApiClient,AuthStore,Models}.swift   # URLSession + Keychain + Codable DTOs
│   │   ├── UI/{AppRoot, Login, Home, Attendance, History, Students}/*.swift
│   │   └── Resources/{Info.plist, Assets.xcassets}
│   ├── scripts/build-ios.sh           # auto-bumps build #, runs xcodegen, archives, exports .ipa
│   └── README.md                      # setup + distribution paths (TestFlight / Ad Hoc / App Store)
├── android/                      # Native Kotlin + Jetpack Compose teacher app (Session 6)
│   ├── app/src/main/java/com/expressonly/kisattendance/
│   │   ├── MainActivity.kt + KisApp.kt
│   │   ├── data/{api,auth,repo}/      # Retrofit + EncryptedSharedPreferences + repos
│   │   ├── di/AppContainer.kt         # manual DI (no Hilt — keeps APK ~3 MB)
│   │   └── ui/{theme,nav,components,screens/{login,home,attendance,history,students,studentdetail}}
│   ├── app/src/main/res/             # adaptive icons (vector), Material3 XML theme, network_security_config
│   ├── app/build.gradle.kts          # AGP 8.5.2, Kotlin 2.0.21, Compose BOM 2024.10.01, minSdk 26 / targetSdk 34
│   ├── keystore/                     # GITIGNORED — kis-release.jks + keystore.properties
│   └── README.md                     # build + sign + sideload instructions
├── deploy/
│   ├── school-management.service # systemd unit (gunicorn + uvicorn workers)
│   ├── nginx.school.conf         # /school/ → static dist; /school/api/ → FastAPI :8000
│   └── .env.example              # DATABASE_URL, JWT_SECRET, CORS_ORIGINS, etc.
├── scripts/build-android.sh      # build signed APK + copy to frontend/public/downloads/
├── scripts/deploy/test/
│   └── deploy-test.sh            # rsync + pip + alembic + systemctl restart + health check
├── _archive/
│   └── index.firebase.html       # OLD Firebase single-file app (reference only)
├── .gitignore
├── README.md
└── .claude/CLAUDE.md             # this file
```

---

## Live URLs
**PROD — kisschool.in (served at ROOT; shared box `69.62.72.137`, key `~/.ssh/enamfoss_prod`, coexists with the enamfoss Tomcat app):**
- Public site `https://kisschool.in/` · Admin portal `https://kisschool.in/admin/` · API `https://kisschool.in/api/` · Health `https://kisschool.in/api/health` · APK `https://kisschool.in/downloads/kis-attendance.apk`

**TEST — expressonly.in/school (box `104.237.5.113`, key `~/.ssh/uploadmytds_test`, shared w/ uploadmytds):**
- Public site `https://expressonly.in/school/` · Admin `…/school/admin/` · API `…/school/api/` · APK `…/school/downloads/kis-attendance.apk` (serves the *staging*-flavor app)

## API Endpoints (REST + SSE)
- **Auth:** `POST /api/auth/login`, `POST /api/auth/change-password`, `POST /api/auth/logout`, `GET /api/auth/me`
- **Students:** `GET/POST /api/students`, `GET/PATCH/DELETE /api/students/{id}`
- **Documents:** `POST /api/students/{id}/documents/{photo|dob_cert|aadhar}` (multipart), `GET /api/files/students/{id}/{kind}` (Bearer) or `…/inline?token=` (for `<img>` tags)
- **Attendance:** `GET /api/attendance?class=&date=`, `PUT /api/attendance`, `GET /api/attendance/today-summary`
- **Marks (legacy free-text):** `POST /api/marks/bulk` + `POST /api/marks/bulk-import` (CSV) write `batch_id=NULL` rows. `GET /api/marks?class=&exam_type=` still pivots all rows for MarksResults.
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

All migrations live under `backend/alembic/versions/`. `0001_initial.py` is the baseline; `0008_class_subjects.py` + `0009_marks_batches_edit_requests.py` are the Session 13 additions. **Never** call `metadata.create_all()`; always use `alembic upgrade head`.

---

## Deployment (test VPS — `104.237.5.113`)

**One-time server setup:**
1. `apt install python3.12 python3.12-venv mysql-client nginx`
2. `mysql -e "CREATE DATABASE school_management CHARACTER SET utf8mb4; CREATE USER 'school'@'localhost' IDENTIFIED BY '<pwd>'; GRANT ALL ON school_management.* TO 'school'@'localhost';"`
3. `useradd --system --home /opt/school-management school`
4. `mkdir -p /opt/school-management/{app,frontend/dist,logs,backups}` and `chown -R school:school /opt/school-management`
5. Place `.env` at `/opt/school-management/.env` (see `deploy/.env.example`).
6. `cp deploy/school-management.service /etc/systemd/system/` then `systemctl daemon-reload && systemctl enable --now school-management`
7. Add `deploy/nginx.school.conf` to your nginx config (inside the existing `expressonly.in` server block) and `nginx -s reload`.
8. Set DNS so `expressonly.in/school/` resolves to this server. Reuse the existing Let's Encrypt cert (it's wildcard for the domain).

**Subsequent deploys (run from local):**
```bash
./scripts/deploy/test/deploy-test.sh
```
Steps it does: AST-parse Python → `npm ci && npm run build` (Vite) → rsync `backend/` and `frontend/dist/` → `pip install -r requirements.txt` → `alembic upgrade head` → `systemctl restart school-management` → health check.

**Default admin login:** `admin` / `admin123` (auto-seeded as bcrypt hash on first boot via `lifespan`). Change immediately via in-app "Change Password".

---

## Frontend Routes
SPA mounted at `/school/admin/` (Vite `base`). Routes:
`/login` (public) · `/dashboard` · `/admissions` · `/students` · `/students/:id?edit=1` · `/attendance` · `/marks/entry` · `/marks/results` · `/fees` (admin) · `/notices` · `/staff` (admin) · `/reports` (admin) · `/letterheads` (admin) · `/salary-slips` (admin) · `/templates` (admin) · `/templates/:id` (admin) · `/class-subjects` (super-admin) · `/class-subjects/:id` (super-admin) · `/deletion-requests` (super-admin) · `/edit-requests` (super-admin — student + marks tabs) · `/mobile-apps`

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

4. **Vite ships everything in `frontend/public/` verbatim into `dist/`.** That's how the Android APK reaches teachers: `scripts/build-android.sh` writes `frontend/public/downloads/kis-attendance.apk` → `npm run build` copies it into `dist/downloads/` → existing rsync deploys it to nginx. **No nginx changes needed** — the existing `alias /opt/school-management/frontend/dist/` already serves arbitrary subpaths under `/school/`. Side effect: the rsync uses `--delete`, so if you ever run `/deploy-test-frontend` *without* first running `bash scripts/build-android.sh`, the public APK URL 404s until the next APK build. Same goes for any future static asset under `public/`.

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

15. **Vite cache-bust contract: embedded `__BUILD_ID__` + `dist/version.json` + runtime poll + nginx no-cache.** Hashed asset filenames bust themselves on rebuild, but cached `index.html` keeps referencing the OLD hashes — that's the "user needs hard refresh after deploy" loop. Session 13 fix in 4 parts: (a) [vite.config.ts](../frontend/vite.config.ts) generates a fresh `BUILD_ID` each build, injects it as `__BUILD_ID__` via `define`, and emits `dist/version.json` via a tiny plugin; (b) [lib/version.ts](../frontend/src/lib/version.ts) `useVersionCheck()` polls `version.json` with `cache: 'no-store'` every 5 min while visible and reloads with a `?_v=<ts>` query-bust on mismatch (the query bust is essential — `window.location.reload()` alone respects the cached HTML); (c) [deploy/nginx.school.conf](../deploy/nginx.school.conf) adds exact-match `location` blocks sending `Cache-Control: no-cache, must-revalidate` for `/school/admin/`, `index.html`, and `version.json`; (d) `define: { __BUILD_ID__: JSON.stringify(...) }` — **must** use `JSON.stringify`, otherwise the substituted string is unquoted and the bundle fails to parse. To roll out the nginx side after first deploy: rerun `bash scripts/provision/06-install-nginx-snippet.sh` or one-shot `scp deploy/nginx.school.conf root@<server>:/etc/nginx/snippets/school.conf && nginx -t && systemctl reload nginx`.

16. **Android R8/ProGuard keep rule must track the package name.** `app/proguard-rules.pro` keeps Gson DTOs by package: `-keep class in.kisschool.data.api.dto.** { *; }`. When the package was renamed `com.expressonly.kisattendance → in.kisschool`, the old keep rule matched nothing → R8 obfuscated DTO field names in the **release** build only → the app sent login as `{"<garbled>":…}` → backend `422` (and every API call broke). Debug builds (no minify) hid it. Fix: keep rule on the new package **plus** `-keepclassmembers,allowobfuscation class * { @com.google.gson.annotations.SerializedName <fields>; }`. Verify via `app/build/outputs/mapping/<flavor>Release/mapping.txt` — the DTO class should map to itself.

17. **`frontend/vite.config.js` is a committed `tsc` artifact and Vite prefers `.js` over `.ts`.** `npm run build` (= `tsc -b && vite build`) regenerates it from `vite.config.ts`, but a bare `npx vite build` uses the STALE `.js`. Base path is build-time parametrized: `vite.config.ts` reads `process.env.VITE_BASE ?? "/school/admin/"`; `VITE_API_URL` is shell-exported (overrides `.env.production`); favicon uses a `%BASE_URL%` placeholder substituted by a `transformIndexHtml` plugin (a plain relative favicon 404s on SPA deep links). `scripts/deploy/<env>/env.sh` sets `VITE_BASE`/`VITE_API_URL`/`SITE_BASE_PATH`/`HEALTH_PATH`/`SITE_URL_PATH` (test → `/school/...`, prod → root). See [[feedback_vite_base_parametrization]].

18. **`GET /api/students` is paginated** (`{items,total,page,page_size}`) — clients must read `.items`. The Android app's bare-`List<StudentDto>` DTO silently broke against the live backend until fixed with a `StudentPageDto` wrapper. Also: `in` is a Kotlin hard keyword, so the `in.kisschool` package must be backtick-escaped (`` `in`.kisschool ``) in every `package`/`import` (Gradle `namespace`/`applicationId` strings don't); and AGP forbids a product-flavor name starting with `test` → the staging flavor is named `staging` with `applicationIdSuffix = ".test"`.

19. **Staff dual-credential temp password (migration 0010).** `staff.temp_password_hash` is a SECOND valid login that does NOT replace `password_hash` — admin/super-admin set it from the web Staff page to cover an absent teacher; login accepts real-OR-temp; a temp login never triggers force-password-change; cleared by admin (no auto-expiry). `POST/DELETE /api/staff/{id}/temp-password`. **Forgot-password (migration 0011)** works for admin/super-admin/staff (`_resolve_reset_account` maps the hardcoded admin emails); needs SMTP set in `.env` (`SMTP_*`, Zoho `info@kisschool.in`) + `APP_BASE_URL=https://kisschool.in/admin` so reset links are correct. The web ForgotPassword form must POST `{identifier}` (not `{email}`).

---

## Status (after this session)
| Area | Status |
|---|---|
| Backend FastAPI app | ✅ Code complete + 4 bulk-import endpoints, AST clean |
| SQLAlchemy models / Alembic baseline | ✅ All 8 entities, `0001_initial` applied on test |
| Auth (JWT + bcrypt + admin seed) | ✅ |
| Routers (auth/students/files/att/marks/fees/notices/staff/reports/stream/health) | ✅ |
| Bulk import (`/api/{students,attendance,staff,marks}/bulk-import`) | ✅ Shared `_bulk.py` helper |
| SSE pub/sub broker | ✅ |
| React frontend | ✅ 12 pages + Layout + ProtectedRoute, BrowserRouter `basename="/school"`, builds clean (206 KB gz) |
| Form validation (Admissions + StudentDetail edit) | ✅ phone/aadhar regex, Title-Case names, religion dropdown, DOB bounds + auto-picker, fee leading-zero fix |
| Bulk import UI (Students / Attendance / Staff / Marks Entry) | ✅ Shared `BulkImportDialog` + templates, inline error banner + table, error report CSV |
| shadcn UI primitives | ✅ Button focus ring, Select tabIndex + visible ring, Dialog/Table/Toast/etc. |
| Server provisioning (idempotent) | ✅ `bash scripts/provision/provision.sh` |
| Test deploy | ✅ Live at https://expressonly.in/school/ (admin/admin123) |
| Reusable deploy framework (test ↔ prod parity) | ✅ `scripts/deploy/{common,test,prod}/` + `scripts/provision/` + `.claude/commands/` |
| Firebase configs deleted, old `index.html` archived | ✅ |
| Modern popover date pickers (replaces native `<input type="date">` everywhere) | ✅ Session 6 — react-day-picker v9 + custom shadcn `DatePicker` on 4 sites (Admissions DOB, StudentDetail DOB, Fees, Attendance) |
| Android teacher attendance app | ✅ Session 6 — Kotlin/Compose, signed v2/v3 release APK (2.9 MB), live at /school/downloads/kis-attendance.apk + "Download for Android" link on web Login |
| Android version mechanism | ✅ Session 6 follow-up — `android/version.properties` + auto-bump `versionCode` in `build-android.sh`; in-app: small footer on Login + "About" dialog from Home menu (both read `BuildConfig`). Currently shipping `v1.0.0 build 2` |
| `/release-android` slash command + APK-only upload script | ✅ Session 6 follow-up — builds, asks `y/N`, then rsyncs ONLY the APK (no SPA rebuild). `scripts/deploy/test/upload-apk.sh` |
| iOS app scaffold (SwiftUI + XcodeGen) | ✅ Session 7 — `ios/` mirrors `android/`: 6 screens (Login/Home/TakeAttendance/History/Students/StudentDetail), URLSession+async/await, Keychain auth store, 401→logout. Compiles+runs in Xcode after `brew install xcodegen && xcodegen`. **Distribution requires Apple Dev account** ($99/yr) — no APK-style sideload on iOS |
| `Mobile Apps` page in web SPA (`/mobile-apps`) | ✅ Session 7 — **LIVE on TEST** at /school/mobile-apps. Sidebar entry under "Resources" section. Two cards: Android (Available, direct APK link) + iOS (Coming soon, TestFlight invite). Replaces the link that was on Login. Login page is now form-only |
| KIS design retrofit (tokens/fonts/i18n/brand) | ✅ Session 8 — `packages/design-system/` shared by React portal + Eleventy public-site + WeasyPrint PDFs. nginx 4-location longest-prefix routing. Public site at /school/, admin at /school/admin/ |
| 6 brand-styled WeasyPrint PDFs (letterheads + fee-receipt + report-card + salary-slip + pseb-admit-card) | ✅ Session 8 — shared `_base.html.j2` with tri-band header + Cinzel motto footer (`position: fixed`) + watermark crest. Bilingual everywhere |
| Admin generation pages (Letterheads + Salary Slips) | ✅ Session 8 — single-shot form → POST `/api/pdf/{kind}` → blob download |
| **Class-templated bulk PDF flow with cache** | ✅ Session 8 — 3 new tables (`pdf_templates`, `pdf_student_data`, `pdf_cache`); admin Templates page with 3-section detail (template form, per-student spreadsheet, bulk-render). Cache keyed by `(kind, student_id, template_id, template_version)`. Editing a template bumps version → cache auto-invalidates. Live and verified end-to-end |
| **Soft-delete + super-admin approval workflow (Session 9)** | ✅ Session 9 — migration `0003_soft_delete_workflow`; new `super_admin_auth` singleton + 6 status columns on students/staff. Routes: `/api/admin/deletion-requests` (list/approve/restore/purge). UI: `/deletion-requests` page (super-admin), badge + reason dialog in Students/Staff pages. Permission matrix: staff/admin → request, super-admin → archive directly + approve/purge. Restore is admin OR super-admin |
| `/check-logs` slash command (Session 9) | ✅ Read-only 6-section SSH log streamer with shorthand windows (`30m`/`2h`/`1d`). Test + Prod variants |
| LogRecord `name` collision bug (Session 9) | ✅ Fixed — see Gotcha #16. Was crashing student-create + delete responses for ~8 days |
| **Dual-mode navigation (Session 12)** | ✅ Top-bar mode (default) with 5 section dropdowns + Sidebar mode (legacy). Hamburger toggles modes on desktop, opens drawer on mobile. `useNavMode` persists choice to `localStorage`. Logout button + user-menu dropdown live in slim topbar. Sidebar/TopNav/Layout split into 3 components consuming a shared `SECTIONS` registry at [lib/nav-sections.ts](../frontend/src/lib/nav-sections.ts) |
| **Class Subjects master + per-subject exam-component editor (Session 13)** | ✅ Migration 0008; super-admin CRUD at `/class-subjects` + spreadsheet-style component editor at `/class-subjects/:id`; "Seed KIS default pattern" one-click materialises 127 subjects + 654 components from the school's exam-pattern sheet across Nursery–12th. Bulk CSV import, category enum, FK CASCADE on component delete |
| **MarksEntry master-bound + per-student validation + roll/parent display (Session 13)** | ✅ Dropdowns bind to class_subjects + subject_exam_components, max marks auto-filled read-only. Server enforces `0 ≤ marks ≤ max_marks` on `POST /marks/bulk` + bulk-import. Student rows show `<roll>  <name>  · S/o <father>` sorted by roll# numerically — disambiguates duplicate names |
| **Marks draft → submit → lock → edit-request workflow (Session 13)** | ✅ Migration 0009; new `marks_batches` + `marks_edit_requests`. 3-state MarksEntry (New/Draft → Submitted+locked → Submitted+pending). Tabbed `/edit-requests` (Student edits / Marks edits) with auto-switch to non-empty queue. Approve flips batch back to draft (no timer); required reason on request; new shadcn `Tabs` primitive |
| **NumberField + global spinner removal + hard-clamp (Session 13)** | ✅ [components/ui/number-field.tsx](../frontend/src/components/ui/number-field.tsx) stores state as string (empty allowed), rejects keystrokes that exceed `max`/`min`, red border on invalid. Spinner arrows hidden globally on `<Input type="number">` — kills the "100 → 31" bug (Gotcha #13) |
| **Auto cache-bust on deploy (Session 13)** | ✅ Vite injects `__BUILD_ID__` + emits `dist/version.json`; `useVersionCheck()` polls every 5 min while visible and reloads with `?_v=<ts>` query bust on mismatch. nginx serves `index.html` + `version.json` with `Cache-Control: no-cache, must-revalidate`. No more "need a hard refresh after deploy" (Gotcha #15) |

---

## Slash Commands (mirror uploadmytds)
| Command | Script | Purpose |
|---|---|---|
| `/provision-test` | `scripts/provision/provision.sh` | One-time TEST server bootstrap (idempotent: prereqs / school user / dirs / MySQL DB+user / .env / systemd unit / nginx snippet) |
| `/deploy-test` | `scripts/deploy/test/deploy-backend.sh` | Backend-only deploy to TEST |
| `/deploy-test-frontend` | `scripts/deploy/test/deploy-frontend.sh` | Frontend-only (Vite build + rsync) |
| `/deploy-test-all` | `scripts/deploy/test/deploy-all.sh` | Backend + frontend with snapshot + auto-rollback |
| `/deploy-prod` `/deploy-prod-frontend` `/deploy-prod-all` | `scripts/deploy/prod/*.sh` | PROD versions; require typing `DEPLOY PROD` to confirm. PROD `env.sh` must have CHANGE_ME placeholders replaced first. |
| `/clean-logs` | local `rm -rf logs_backup_*` | Clean local log-backup dirs (after explicit y) |
| `/release-android` | `scripts/build-android.sh` + `scripts/deploy/test/upload-apk.sh` (gated by `y/N`) | Build a fresh signed APK, then ask before uploading just the APK file to TEST. Skips the SPA rebuild — the web download link is already deployed |
| `/check-logs` | `scripts/deploy/test/check-logs.sh` (also `prod/`) | Read-only log analysis: 6 sections (service status / journalctl / error.log tail / recent tracebacks / access.log tail / 4xx-5xx). Accepts `30m`, `2h`, `1d`. Nothing written, nothing downloaded — single SSH session straight to terminal |
| `/save-session` | (skill) | Snapshot session context to `.claude/CLAUDE.md` + memory files |

Other manual scripts: `scripts/deploy/test/download-logs.sh` · `backup-db.sh` · `rollback.sh <timestamp>`. Same set under `scripts/deploy/prod/`. Plus `scripts/build-android.sh` (release APK build + copy to `frontend/public/downloads/`).

## Server-side Layout (post-provisioning, on 104.237.5.113)
```
/opt/school-management/                 (chmod 755 school:school)
├── app/                                rsynced from backend/
│   └── .venv/                          created on first deploy
├── frontend/dist/                      rsynced from frontend/dist/
├── logs/                               gunicorn access/error logs
├── backups/                            app_<ts>.tgz + db_<ts>.sql.gz (auto-pruned >30d)
├── .env                                secrets (chmod 600 school:school)
├── .my.cnf                             mysqldump credentials (chmod 600 school:school)
└── .db_password                        DB password (chmod 600 root, kept for re-provision)

/etc/systemd/system/school-management.service    gunicorn -w 2 :8000 (Restart=on-failure)
/etc/nginx/snippets/school.conf                  /school/ alias + /school/api/ proxy
                                                 included from `expressonly.in` SSL block in /etc/nginx/sites-enabled/test-angular
```

## Promoting test → prod (future)
1. Edit `scripts/deploy/prod/env.sh` (replace `CHANGE_ME_PROD_IP`, `CHANGE_ME_PROD_DOMAIN`).
2. `ssh-keygen -t ed25519 -f ~/.ssh/school-management_prod` then `ssh-copy-id` to prod box.
3. `SERVER=<prod-ip> SSH_KEY=~/.ssh/school-management_prod DOMAIN=<prod-domain> bash scripts/provision/provision.sh` (one-time).
4. `bash scripts/deploy/prod/deploy-all.sh` (every release).

## Next Steps (TODOs)
0. **(Session 16 open)** Push `dev` to origin (2 commits `79b9eed` + `60133ff` unpushed). Super-admin password is no longer `super123` (unknown) — reset on both servers if needed (now identical test↔prod). Optionally downscale the Android document-photo upload (web compresses to ~900px; the app currently uploads the original). The `## Promoting test → prod` section below is now historical — prod is live; deploy via `scripts/deploy/prod/*` with key `~/.ssh/enamfoss_prod`.
1. **Change default password** — `admin123` still the seed for admin on both servers; change via in-app Change Password.
2. **Migration for `admission_no` / `admission_id` / `roll_no`** — Student model + schema were extended with these columns post-Session-9 (intentional user edits), but no Alembic migration was written yet. Add `admission_no INT NULL`, `admission_id VARCHAR(32) NULL UNIQUE`, `roll_no VARCHAR(20) NULL` + composite UNIQUE `(class_name, roll_no)`. Backend logic + frontend already expects these.
3. **Verify the seeded exam pattern** — Session 13's `seed-defaults` materialised 127 subjects + 654 components hand-derived from the school's handwritten PDF. Some 9th–10th values are ambiguous (grand totals don't quite match 1900); super-admin should spot-check each class against the original sheet before relying on these for actual exams. Edit in [seed/exam_pattern.py](../backend/app/seed/exam_pattern.py) and re-seed on a fresh DB, or tweak per-row via the UI.
4. **Optional: backfill legacy `marks.batch_id`** — pre-Session-13 mark rows have NULL `batch_id` (and likely duplicates from re-saves). One-shot script grouped by `(class, subject, exam_type, session)` to create draft batches + reassign rows would let teachers manage old data through the new lock workflow. Currently they're tolerated as read-only legacy.
5. **Polish per-page bilingual** (Sprint 4 partial) — login + sidebar + Templates + Deletion Requests bilingual; Students/Attendance/Marks/Fees/Staff/Reports table headers + form labels still English-only. Wrap with `<T k="…">` and add keys under `portal.<page>.*`.
6. **Sprint 6 — STATUS.md + Lighthouse + axe** — final design-handoff report.
7. **Verify iOS build locally** — install Xcode + `brew install xcodegen`, then `cd ios && xcodegen && open KisAttendance.xcodeproj`. SwiftUI source compiled by Claude only.
8. **Decide on Apple Developer Program** ($99/yr) — gates iOS distribution. Once enrolled, flip `method=app-store` in [ios/scripts/build-ios.sh](../ios/scripts/build-ios.sh) and update the iOS card on `/mobile-apps`.
9. **Auto DB backup** — APScheduler in `app/main.py` lifespan or server cron `mysqldump school_management | gzip > /opt/school-management/backups/$(date +%F).sql.gz` every 24h.
10. **Bulk-import attendance UX** — wide-format template that pre-fills the student roster.
11. **Code-split frontend** — bundle now 965 KB / 293 KB gz; Chart.js ~half. Lazy-load report + template + class-subjects routes if pages keep growing.
12. **Templated PDF v2 follow-ups** — async render with SSE progress events for >30-student bulk runs; ZIP-of-many download; orphan-cache cleanup cron; allow class-scoped Staff to *render* (not edit) templates.
13. **MarksResults v2** — now that marks have `(class, subject, exam_type, session)` batches with `max_marks`, the pivot can show a true `%` (current code assumes max=100/subject) and filter by session. Also surface batch-status badges so teachers see which subjects are still draft.
14. **Optional later:** Redis pub/sub for SSE if scaling to >1 gunicorn worker; rate limiting on `/auth/login`; structured JSON logging.

---

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
> Session 14 (Android force-update gate) + 15 (Android dashboard + back-dated attendance, v1.2.3) — see memory `project_android_force_update` / `project_android_dashboard_attendance`

### Session 16 — 2026-06-06 · PROD launch at kisschool.in + Android `in.kisschool` rebrand + temp-password + forgot-password

**Focus:** Stand up a dedicated production environment and a batch of cross-cutting features.

**(A) PROD at kisschool.in (served at ROOT).** New dedicated domain on a SHARED box `69.62.72.137` (key `~/.ssh/enamfoss_prod`) that already runs a Java/Tomcat "enamfoss" app (bare-IP vhost). Installed MySQL 8 + certbot; new **standalone** nginx vhost [deploy/nginx.kisschool.conf](../deploy/nginx.kisschool.conf) (`/`=public site, `/admin/`=SPA, `/api/`=FastAPI, `/downloads/`). **Base-path parametrized** so one source ships to TEST (`/school/...`) and PROD (root): `VITE_BASE`/`VITE_API_URL`/`SITE_BASE_PATH`/`HEALTH_PATH`/`SITE_URL_PATH` in `scripts/deploy/<env>/env.sh`, consumed by `common/lib.sh`; `vite.config.ts` base + `public-site/src/_data/site.cjs` basePath read env (test defaults) — see Gotcha #17. Filled `scripts/deploy/prod/env.sh`; added `scripts/deploy/prod/{deploy-public-site,upload-apk}.sh`. **Migrated master data** test→prod (staff+staff_classes, students+documents, class_subjects+subject_exam_components) via streamed mysqldump.

**(B) Android `in.kisschool` rebrand + features.** Package renamed `com.expressonly.kisattendance → in.kisschool` (backtick-escaped `in` keyword everywhere). **Product flavors** `prod` (`in.kisschool`, kisschool.in/api) + `staging` (`in.kisschool.test`, expressonly.in/school/api) via `BuildConfig.API_BASE_URL`; `build-android.sh {prod|test}` + force-update gate ([release-android](./commands/release-android.md) publishes `app-version.json`). New app screens: **Login** redesigned to match web (gradient/crest/remember-me + Forgot-password link); **Edit Student** (full validation + staff edit-request workflow) with **document upload/preview** (Coil, photo/dob_cert/aadhar); **Marks Entry** (draft→submit→lock→request-edit). Fixed `/students` pagination DTO (Gotcha #18) and the **R8 keep-rule → login 422** bug (Gotcha #16). Both APKs rebuilt + deployed per server.

**(C) Auth: temp-password + forgot-password + gmail admin logins.** Admin/super-admin login identifiers → `nsnishasaini57@gmail.com` / `gssonusaini57@gmail.com`. **Migration 0010** staff `temp_password_hash` (admin-set 2nd credential, web Staff page; login accepts real-OR-temp). **Migration 0011** `password_reset_tokens` — forgot/reset works for admin/super-admin/staff; SMTP (Zoho `info@kisschool.in`) + `APP_BASE_URL=https://kisschool.in/admin` configured on prod; fixed web ForgotPassword form to POST `{identifier}`. See Gotcha #19. Copied admin/super-admin password hashes test→prod so both match.

**Deploys:** prod provisioned + `deploy-prod-all`/`-frontend`/`-backend`/`-public-site`; test brought to parity (`deploy-test-all` + frontend). Migrations on prod: …→0009→0010→0011. **Commits:** `79b9eed` (big), `60133ff` (forgot-form fix) on `dev` — **not pushed**. Open TODO: push `dev`; super-admin password is not `super123` (reset if unknown); downscale app photo uploads (web compresses, app sends original).

### Session 13 — 2026-05-24 · Class Subjects master + Marks draft/submit/lock/edit-request workflow + auto cache-bust

**Focus:** Three independent features that landed in a single multi-stage session.

**(A) Class Subjects master + per-subject exam-component editor** ([migration 0008](../backend/alembic/versions/0008_class_subjects.py)) — super-admin owns a `(class, subject)` master plus a nested `(component_name, max_marks, order)` editor per subject. Migration adds `class_subjects` (with `category` ENUM `academic|co_curricular|grading`) + `subject_exam_components` (FK CASCADE on subject delete). Backend: [routers/class_subjects.py](../backend/app/routers/class_subjects.py) ships subject CRUD + bulk-import + nested component CRUD + a `PUT /{id}/components` atomic-replace endpoint for the spreadsheet editor. Seed module [seed/exam_pattern.py](../backend/app/seed/exam_pattern.py) materialises the school's full handwritten exam pattern — **127 subjects, 654 components** across Nursery → 12th, including practical splits (Maths/Science 70W+10P in 6–10, Phy.Edu 50W+30P in 11–12), Punjabi-PT=25 in 9–10, co-curricular sets for NUR/LKG/UKG. Frontend: [pages/ClassSubjects.tsx](../frontend/src/pages/ClassSubjects.tsx) list page with "Seed KIS default pattern" button + [pages/ClassSubjectDetail.tsx](../frontend/src/pages/ClassSubjectDetail.tsx) spreadsheet editor. Nav entry under Academic, super-admin-only.

**(B) Marks Entry: master-binding + draft → submit → lock → edit-request workflow** ([migration 0009](../backend/alembic/versions/0009_marks_batches_edit_requests.py)) — MarksEntry was rewritten in two passes. First pass made class/subject/test all dropdowns bound to the new master, with auto-filled read-only max marks and per-student validation (`marks ≤ max_marks` on client + server). Then the draft/lock workflow: new `marks_batches` table keyed on `(class, subject, exam_type, session)` with `status ∈ {draft, submitted}` + `submitted_at/by`; `marks.batch_id` FK with **UNIQUE(batch_id, student_id)** giving free upsert (Gotcha #14); new `marks_edit_requests` table mirroring `student_edit_requests`. Router [routers/marks_batches.py](../backend/app/routers/marks_batches.py): `GET /marks/batches?class=&subject=&exam_type=&session=` returns batch+items or null; `POST /marks/batches` upserts (refuses submitted batch for non-super-admin); `POST /{id}/submit` locks; `POST /{id}/request-edit` enqueues a request with required reason; super-admin queue under `/admin/marks-edit-requests`. Approve flips batch back to `draft` indefinitely (no timer, teacher re-submits manually); reject keeps it locked with reason banner. Frontend: 3-state MarksEntry (New/Draft → Submitted+locked → Submitted+pending) + tabbed [pages/EditRequests.tsx](../frontend/src/pages/EditRequests.tsx) — "Student edits" tab unchanged, new "Marks edits" tab with same review-modal UX, default tab auto-switches to whichever queue has pending items. New shadcn `Tabs` primitive at [components/ui/tabs.tsx](../frontend/src/components/ui/tabs.tsx). Bulk-import endpoint `POST /marks/bulk-import` stays as a legacy free-text path (writes `batch_id IS NULL`).

**(C) NumberField + auto cache-bust** — two cross-cutting UX fixes. `NumberField` ([components/ui/number-field.tsx](../frontend/src/components/ui/number-field.tsx)) wraps `<Input type="number">` with empty-string-friendly state + hard-clamp-on-keystroke (rejects values > max or < min) — fixes the "100 → 31" teacher bug (Gotcha #13). Spinner arrows hidden globally in [input.tsx](../frontend/src/components/ui/input.tsx). Auto cache-bust ([vite.config.ts](../frontend/vite.config.ts) + [lib/version.ts](../frontend/src/lib/version.ts) + nginx) means deploys propagate to open browser tabs within 5 minutes without hard-refresh (Gotcha #15).

**Display polish:** MarksEntry student rows now show `<roll#>  <name>  · S/o <father>`, sorted by roll# numerically — disambiguates duplicate names (e.g. two "Manveer Singh" in L.K.G).

**Deploys:** four `/deploy-test-frontend` for incremental rollouts + two `/deploy-test-all` for migration 0008 and 0009. Snapshots retained: `app_20260523_220103.tgz`, `app_20260523_222025.tgz`, `app_20260524_000020.tgz`. Bundle: 949–965 KB JS / 288–293 KB gz (+18 KB gz total this session: NumberField + tabs primitive + version probe + marks workflow). nginx snippet hot-applied via SSH (user-authorised). Migration 0009 ran cleanly: `0008_class_subjects → 0009_marks_batches_edit_requests`.

**Plan file:** `/Users/manjeetsaini/.claude/plans/add-draft-functionaly-to-merry-popcorn.md` (approved + executed).


---

## Documentation
- Old single-file Firebase app (read-only reference): [_archive/index.firebase.html](../_archive/index.firebase.html)
- Bootstrap → Tailwind migration handled inside the React rewrite
- shadcn/ui: https://ui.shadcn.com/
- TanStack Query: https://tanstack.com/query/v5
- FastAPI: https://fastapi.tiangolo.com/
- Alembic: https://alembic.sqlalchemy.org/
- Architecture plan: [/Users/manjeetsaini/.claude/plans/create-a-deep-plan-snug-tome.md](/Users/manjeetsaini/.claude/plans/create-a-deep-plan-snug-tome.md)

> Context usage guide: 0–60% work freely | 60–70% monitor usage | 70–80% run /compact | 80%+ run /clear (mandatory)
