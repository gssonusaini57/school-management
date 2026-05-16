# Project Memory
**Last Updated:** 2026-05-16 | **Sessions:** 9 (1–6 archived) | **Branch:** master | **Stage:** ✅ DEPLOYED — web + signed Android APK + iOS scaffold + **two-tier soft-delete + super-admin approval workflow on Students/Staff (Session 9)**. Public site at https://expressonly.in/school/, admin at /school/admin/. Default logins: `admin / admin123`, `superadmin / super123` — change both after first real use.

> Slash commands: see [.claude/commands/](./commands/) — `/provision-test`, `/deploy-test`, `/deploy-test-frontend`, `/deploy-test-all`, `/deploy-prod*`, `/clean-logs`, `/check-logs`, `/release-android`, `/save-session`. Android APK build: `bash scripts/build-android.sh` (no slash command — runs locally with the keystore).

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

## Live URLs (after deploy)
- Public site: `https://expressonly.in/school/`
- Admin portal: `https://expressonly.in/school/admin/`  (login `admin/admin123`)
- API: `https://expressonly.in/school/api/`
- Health: `https://expressonly.in/school/api/health`
- SSE streams: `https://expressonly.in/school/api/stream/{students|fees|notices|staff|dashboard}?token=<jwt>`

## API Endpoints (REST + SSE)
- **Auth:** `POST /api/auth/login`, `POST /api/auth/change-password`, `POST /api/auth/logout`, `GET /api/auth/me`
- **Students:** `GET/POST /api/students`, `GET/PATCH/DELETE /api/students/{id}`
- **Documents:** `POST /api/students/{id}/documents/{photo|dob_cert|aadhar}` (multipart), `GET /api/files/students/{id}/{kind}` (Bearer) or `…/inline?token=` (for `<img>` tags)
- **Attendance:** `GET /api/attendance?class=&date=`, `PUT /api/attendance`, `GET /api/attendance/today-summary`
- **Marks:** `POST /api/marks/bulk`, `GET /api/marks?class=&exam_type=`
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
- **Realtime:** `GET /api/stream/{students|fees|notices|staff|dashboard}?token=<jwt>`

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
| marks | id BIGINT | INDEX(class_name, exam_type) — replaces compound Firestore query |
| fee_payments | id BIGINT | receipt_no UNIQUE, denormalized student_name |
| notices | id BIGINT | priority ENUM, audience |
| pdf_templates | id BIGINT | (kind, class_name, session, term_key) UNIQUE; `data` JSON validated by Pydantic on save; `version` int bumps on PATCH |
| pdf_student_data | id BIGINT | (kind, student_id, session, term_key) UNIQUE; `data` JSON; one row per student per (kind, session, term) |
| pdf_cache | id BIGINT | (kind, student_id, template_id, template_version) UNIQUE; `data` LONGBLOB; FK CASCADE on template + student |

All migrations live under `backend/alembic/versions/`. `0001_initial.py` is the baseline; `0002_pdf_templates_cache.py` adds the 3 templated-PDF tables (Session 8). **Never** call `metadata.create_all()`; always use `alembic upgrade head`.

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
`/login` (public) · `/dashboard` · `/admissions` · `/students` · `/students/:id?edit=1` · `/attendance` · `/marks/entry` · `/marks/results` · `/fees` (admin) · `/notices` · `/staff` (admin) · `/reports` (admin) · `/letterheads` (admin) · `/salary-slips` (admin) · `/templates` (admin) · `/templates/:id` (admin) · `/mobile-apps`

Sidebar sections: Main · Academic · Administration · **Stationery** (Letterheads / Salary Slips / Templates) · Resources. The `Templates` page replaced the old single-shot `/pseb-admit-card` (Session 8); the per-row report-card download on MarksResults is gone, replaced by a banner pointing at /templates.

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

1. **React Router needs `basename` when the SPA isn't at root.** Without it, `<NavLink to="/admissions">` produces `/admissions` (which nginx routes to uploadmytds's catch-all) instead of `/school/admin/admissions`. [frontend/src/main.tsx](../frontend/src/main.tsx) reads `import.meta.env.BASE_URL` and feeds it to `<BrowserRouter basename={...}>`. The `api.ts` 401 redirect also derives `/school/admin/login` from `BASE_URL` — never hardcode `/login`. Same code Just Works if you ever deploy to root.

2. **Empty array `[]` is truthy with `??`.** Admin's JWT has `allowed_classes: []` (full access marker). Code like `user?.allowed_classes ?? CLASSES` keeps the empty list and dropdowns render zero items. Use `user?.allowed_classes?.length ? user.allowed_classes : CLASSES` everywhere a class dropdown is filtered.

3. **Number inputs default-`0` = leading-zero edit pain.** With `value={form.annual_fee}` initialised to `0`, typing "500" produces "0500" because state is "0" not "". Fix: use `""` as the initial state for numeric form fields, treat empty as `0` at submit (`Number(form.annual_fee) || 0`). For edit pages, also display `""` when the existing value is `0` so users don't have to delete a leading zero before typing.

4. **Bulk-import errors in the dialog (not the toast).** Toasts auto-dismiss after 4s; per-row CSV errors need to stay on screen so the user can read each reason and fix the file. [BulkImportDialog](../frontend/src/components/BulkImportDialog.tsx) renders a sticky-header table of `(row, reason, offending value)` plus a top-level red banner for HTTP/network failures, and the Upload button morphs to "Try again" so users iterate without closing the dialog. Also includes a "Download error report" CSV with all failed rows + reasons + original column data.

5. **Bulk-import endpoints share `backend/app/routers/_bulk.py`.** Helpers: `read_csv` (handles BOM), `title_case`, `parse_date_field`, `must_str`, `opt_str`. Each `/api/<entity>/bulk-import` follows the same shape — try-per-row, validate, accumulate `errors[]`, commit valid rows in one `db.commit()`. Response is always `{inserted: N, errors: [{row, reason, data}]}`. Frontend consumes via shared [BulkImportDialog](../frontend/src/components/BulkImportDialog.tsx) + per-page [templates.ts](../frontend/src/lib/templates.ts).

6. **Android release keystore is irreplaceable.** Once you ship an APK signed with `android/keystore/kis-release.jks`, every subsequent update for *every* phone with the app installed must be signed with the **same** keystore. Lose the .jks (or its password in `keystore.properties`) and you cannot ship updates — phones will refuse to install over the existing app. **Always back up both files** (1Password / Drive / encrypted USB) outside the repo. Both are gitignored (`android/keystore/*.jks`, `android/keystore/keystore.properties`). Current test keystore was generated with a 32-char hex random password; if the user ever wants to re-key for prod / Play Store, they need to commit to the new keystore from day one.

7. **Native `<input type="date">` is banned in this repo.** Browser-native date pickers had two real bugs users hit: (a) Safari's mm/dd/yyyy subfield Tab-trap, (b) year navigation broken on Chrome/macOS, (c) popup not closing after select. All 4 places (Admissions DOB, StudentDetail DOB edit, Fees payment date, Attendance class date) now use [`<DatePicker>`](../frontend/src/components/ui/date-picker.tsx) — popover-based with year/month dropdowns, auto-closes on selection, accepts `min`/`max` ISO strings. Built on `@radix-ui/react-popover` + `react-day-picker@9` + `date-fns`. **For any new date input: import `DatePicker` from `@/components/ui/date-picker`, never re-introduce `<Input type="date">`.**

8. **Vite ships everything in `frontend/public/` verbatim into `dist/`.** That's how the Android APK reaches teachers: `scripts/build-android.sh` writes `frontend/public/downloads/kis-attendance.apk` → `npm run build` copies it into `dist/downloads/` → existing rsync deploys it to nginx. **No nginx changes needed** — the existing `alias /opt/school-management/frontend/dist/` already serves arbitrary subpaths under `/school/`. Side effect: the rsync uses `--delete`, so if you ever run `/deploy-test-frontend` *without* first running `bash scripts/build-android.sh`, the public APK URL 404s until the next APK build. Same goes for any future static asset under `public/`.

9. **`Theme.Material3.*` XML themes need `com.google.android.material:material`.** AGP doesn't include the Google Material Components library by default — only Compose Material 3 (which is a runtime-only Kotlin library, no XML resources). When the manifest references `Theme.Material3.DayNight.NoActionBar` for the Activity, AAPT errors with "resource style not found" unless you add `implementation("com.google.android.material:material:1.12.0")` to [android/app/build.gradle.kts](../android/app/build.gradle.kts). Adds ~700 KB but is the standard pattern for any Compose app that uses an XML theme parent.

10. **`rememberScrollState()` is itself `@Composable` — don't wrap it in `remember{}`.** Compose has two flavors of remember: composable factories like `rememberScrollState()`, `rememberCoroutineScope()`, `rememberDatePickerState()` already memoize their result. Wrapping them in another `remember { ... }` (whose lambda is non-composable) gives "Composable invocations can only happen from the context of a @Composable function." Just call them directly: `val scroll = rememberScrollState()`, not `val scroll = remember { rememberScrollState() }`.

11. **Android version is single-source-of-truth at [android/version.properties](../android/version.properties).** Both `versionCode` and `versionName` live there; `app/build.gradle.kts` reads them at configure time. Don't hardcode versions in `defaultConfig {}`. `scripts/build-android.sh` auto-increments `versionCode` on every release build (commits the new value back to the file), so build numbers are monotonic and unique across machines without manual bookkeeping. **`versionName` stays manual** — edit `version.properties` directly when you want a user-visible bump (e.g. 1.0.0 → 1.1.0). The Login footer + Home → About dialog both read from `BuildConfig.VERSION_NAME` / `VERSION_CODE`, so they never drift from the actual APK metadata.

12. **SQLAlchemy `Enum(MyEnum)` persists Python attribute names by default — not the `.value`.** With a hyphenated MySQL ENUM column (`Enum("report-card", "pseb-admit-card")`) and a Python enum like `class TemplateKind(str, enum.Enum): pseb_admit_card = "pseb-admit-card"`, the default sends `"pseb_admit_card"` (attribute name with underscore) and MySQL replies `Data truncated for column 'kind'` (errno 1265). Fix: `Enum(TemplateKind, values_callable=lambda obj: [e.value for e in obj], native_enum=False, length=32)`. Lives in [backend/app/models/pdf_template.py](../backend/app/models/pdf_template.py).

13. **FastAPI router order matters when path-params can shadow specific routes.** The legacy `pdf` router has `POST /pdf/{kind}` (catch-all). Registering `pdf_templates` AFTER it makes `POST /pdf/templates` resolve to the catch-all with `kind="templates"` instead of the templates router. **Always register the more-specific router first.** [backend/app/main.py](../backend/app/main.py) registers `pdf_templates.router` and `pdf_templates.cache_router` BEFORE the `api_routers` loop that includes `pdf`.

14. **WeasyPrint `position: absolute; bottom: 0` collapses on short content.** When the body content is shorter than the page (e.g. a 3-line letter), the wrapper element is sized to its content and `bottom: 0` anchors the footer to wherever content ends — not to the A4 page bottom. Switch to `position: fixed; bottom: 0`: WeasyPrint treats fixed elements as "render on every page" and pins them to the printable-area bottom regardless of content. Add `padding-bottom: 42px` on the page wrapper so body content can't slide underneath. Verified across all 5 brand-frame docs: footer y_from_bottom 7–8pt (its own internal padding). Lives in [backend/app/pdf/templates/_base.html.j2](../backend/app/pdf/templates/_base.html.j2). Same trick used for the PSEB signatures block.

15. **KIS crest PNGs are 5:4 landscape (256×204 / 1024×816), not square.** Forcing `h-11 w-11` squashes them. Always `h-X w-auto` with the correct intrinsic `width`/`height` attrs (e.g. `width=70 height=56`). Used across [Login.tsx](../frontend/src/pages/Login.tsx), [header.njk](../public-site/src/_includes/header.njk), [_base.html.j2](../backend/app/pdf/templates/_base.html.j2). Same goes for any future logo asset — keep aspect ratio honest.

16. **`log.info("...", extra={"name": ...})` crashes with `KeyError: "Attempt to overwrite 'name' in LogRecord"`.** Python's `logging.LogRecord` reserves a long list of built-in attribute names — passing any of them via `extra=` raises a hard `KeyError` in `makeRecord` (logging/__init__.py:1656). **Reserved keys to avoid:** `name`, `msg`, `args`, `levelname`, `levelno`, `pathname`, `filename`, `module`, `exc_info`, `exc_text`, `stack_info`, `lineno`, `funcName`, `created`, `msecs`, `relativeCreated`, `thread`, `threadName`, `processName`, `process`, `message`. **In this repo:** rename to `student_name` / `staff_name` / `entity_name` etc. The crash bites *after* the DB commit, so requests fail with a 500 even though the write succeeded — silent data hazard. Bug was live for ~8 days (Session 8 through 9) before the new server-log inspection caught it. Caught and fixed in Session 9 students.py:167, staff.py, and the new soft-delete handlers.

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
1. **Change default passwords** — both `admin / admin123` AND `superadmin / super123` are at seed defaults on TEST. Use in-app Change Password dialog the moment a real human logs in.
2. **Migration for `admission_no` / `admission_id` / `roll_no`** — Student model + schema were extended with these columns post-Session-9 (intentional user edits), but no Alembic migration was written yet. Add `admission_no INT NULL`, `admission_id VARCHAR(32) NULL UNIQUE`, `roll_no VARCHAR(20) NULL` + composite UNIQUE `(class_name, roll_no)`. Backend logic + frontend already expects these.
3. **Polish per-page bilingual** (Sprint 4 partial) — login + sidebar + new Templates + Deletion Requests pages are bilingual; Students/Attendance/Marks/Fees/Staff/Reports table headers + form labels still English-only. Wrap with `<T k="…">` and add keys under `portal.<page>.*`.
3. **Sprint 6 — STATUS.md + Lighthouse + axe** — final design-handoff report.
4. **Verify iOS build locally** — install Xcode + `brew install xcodegen`, then `cd ios && xcodegen && open KisAttendance.xcodeproj`. SwiftUI source compiled by Claude only.
5. **Decide on Apple Developer Program** ($99/yr) — gates iOS distribution. Once enrolled, flip `method=app-store` in [ios/scripts/build-ios.sh](../ios/scripts/build-ios.sh) and update the iOS card on `/mobile-apps`.
6. **Auto DB backup** — APScheduler in `app/main.py` lifespan or server cron `mysqldump school_management | gzip > /opt/school-management/backups/$(date +%F).sql.gz` every 24h.
7. **Bulk-import attendance UX** — wide-format template that pre-fills the student roster.
8. **Code-split frontend** — bundle 866 KB / 267 KB gz; Chart.js ~half. Lazy-load report + template routes if pages keep growing.
9. **Templated PDF v2 follow-ups** — async render with SSE progress events for >30-student bulk runs; ZIP-of-many download; orphan-cache cleanup cron; allow class-scoped Staff to *render* (not edit) templates.
10. **Optional later:** Redis pub/sub for SSE if scaling to >1 gunicorn worker; rate limiting on `/auth/login`; structured JSON logging.

---

## Session History

> Sessions 1–2 (Firebase era, pre-migration) archived → see [SESSION_HISTORY_1_2.md](./SESSION_HISTORY_1_2.md)
> Session 3 (FastAPI/MySQL migration scaffold) archived → see [SESSION_HISTORY_3.md](./SESSION_HISTORY_3.md)
> Session 4 (Production deploy + reusable infra) archived → see [SESSION_HISTORY_4.md](./SESSION_HISTORY_4.md)
> Session 5 (UX hardening + bulk import) archived → see [SESSION_HISTORY_5.md](./SESSION_HISTORY_5.md)

### Session 9 — 2026-05-16 · Soft-delete + super-admin approval workflow + /check-logs

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
- New optional Student columns `admission_no` (int), `admission_id` (derived `KIS/{year}/{admission_no:04d}`, UNIQUE), `roll_no` (UNIQUE per class). Pre-flight `_check_uniqueness` returns 409 with conflicting student name. **No Alembic migration yet** — TODO #2.
- Login.tsx: `<Navigate to="/dashboard" replace />` early return when already authenticated. The conditional return runs before `useEffect` below it (Rules-of-Hooks edge case); works in practice but flag if linter errors.

### Session 8 — 2026-05-08 (late) · KIS design retrofit + Stationery + class-templated bulk PDF flow

**Focus:** Apply the KIS brand handoff (tokens, fonts, bilingual i18n, brand SVGs); ship 6 brand-styled WeasyPrint PDF templates with admin generation pages; then design + implement a class-templated bulk PDF flow with server-side cache for Report Cards and PSEB Admit Cards.

**Design retrofit (Sprints 1–5 — earlier in the session):**
- `packages/design-system/` workspace with KIS tokens (Khalsa Blue / Royal Gold / Sangat Red / Vasant Cream / Deep Indigo), fonts (Playfair Display · Cinzel · Cormorant Garamond · Manrope · Noto Sans Gurmukhi), brand crest PNGs at native 5:4 aspect, en+pa i18n.
- React portal: route split, Vite `base` moved to `/school/admin/`, `LocaleSwitch` topbar, `<T>` wrapper, KIS-styled shadcn primitives.
- Public site: standalone Eleventy + Tailwind CLI build at `public-site/` deployed to nginx at `/school/`.
- nginx 4-location longest-prefix routing: `/school/api/` → FastAPI :8000, `/school/admin/` → React dist, `/school/downloads/` → APK, `/school/` → public-site dist.
- 6 PDF templates ([backend/app/pdf/templates/](../backend/app/pdf/templates/)): `_base.html.j2` shared brand frame (tri-band header `blue/gold/red`, Cinzel motto footer "VIDYA · VICHAR · SEVA · EST. 2005", watermark crest); kind-specific: letterhead-a (classic centered seal), letterhead-b (modern asymmetric with gold ribbon), fee-receipt (Format C with itemized table), report-card, salary-slip (gradient net-pay banner), pseb-admit-card.
- Admin generation pages: [Letterheads.tsx](../frontend/src/pages/Letterheads.tsx) (Format A/B picker), [SalarySlips.tsx](../frontend/src/pages/SalarySlips.tsx) (staff picker + earnings/deductions + live net-pay).
- Footer fix: switched from `position:absolute` (collapses on short content) → `position:fixed` (WeasyPrint repeats per page → reliable A4-bottom anchor). Verified: footer y_from_bottom 7–8pt across all 5 brand-frame docs, signatures 45pt on PSEB. Gotcha #14.
- Logo aspect: source PNGs are 256×204 / 1024×816 (5:4 landscape), not square. Use `h-X w-auto` everywhere, never fixed `wxh`. Gotcha (rolled into Conventions).

**Templated bulk PDF flow (Sprint 7 — second half of the session, the user-driven feature):**
- 3 new tables ([backend/alembic/versions/0002_pdf_templates_cache.py](../backend/alembic/versions/0002_pdf_templates_cache.py)):
  - `pdf_templates` — class-level config keyed by `(kind, class_name, session, term_key)`; `data` JSON validated by Pydantic on save; `version` bumps on PATCH.
  - `pdf_student_data` — per-student fields keyed by `(kind, student_id, session, term_key)`; `data` JSON; one row per student per term.
  - `pdf_cache` — generated PDF blobs keyed by `(kind, student_id, template_id, template_version)`; LONGBLOB; CASCADE on template + student delete.
- Pydantic split in [backend/app/pdf/schemas.py](../backend/app/pdf/schemas.py): `ReportCardTemplateData` / `ReportCardStudentData` / `PsebAdmitCardTemplateData` / `PsebAdmitCardStudentData`. `TEMPLATE_SCHEMA_BY_KIND` and `STUDENT_DATA_SCHEMA_BY_KIND` indexed by kind.
- Builder ([backend/app/pdf/builder.py](../backend/app/pdf/builder.py)) merges (template + student row + per-student data + Marks rows for report cards) → validated full ReportCard / PsebAdmitCard model. Auto-grades from marks; defaults bilingual fields when only EN provided.
- Cache logic ([backend/app/pdf/render_or_cache.py](../backend/app/pdf/render_or_cache.py)) — lookup `(kind, student_id, template_id, version)` → render-on-miss → store LONGBLOB → return result row. `force=True` bypasses cache.
- Router ([backend/app/routers/pdf_templates.py](../backend/app/routers/pdf_templates.py)) — templates CRUD + per-student data upsert + roster + bulk render + cache blob serve. Two FastAPI routers (`/pdf/templates` + `/pdf/cache`) registered BEFORE the legacy `/pdf/{kind}` router so the catch-all path-param doesn't shadow `/pdf/templates`. Gotcha #13.
- Legacy `POST /api/pdf/{report-card,pseb-admit-card}` returns **410 Gone** with a "use templates flow" message; the other 4 ad-hoc kinds (letterhead-a/b, fee-receipt, salary-slip) still work.
- Frontend: [Templates.tsx](../frontend/src/pages/Templates.tsx) (list + new-template dialog) and [TemplateDetail.tsx](../frontend/src/pages/TemplateDetail.tsx) with 3 stacked sections — class-level form (kind-aware), per-student spreadsheet (dynamic columns by kind, single "Save N changes" button), bulk-render panel (checkbox-list, "Force re-render" toggle, per-row status `cached/rendered/error`, download links).
- Cleanup: deleted `frontend/src/pages/PsebAdmitCard.tsx`; removed per-row report-card download from MarksResults (now shows a banner pointing at Templates); sidebar "Stationery" section: Letterheads · Salary Slips · **Templates** (replaces standalone PSEB).

**Verified live (E2E smoke):**
- Render call 1 → `status=rendered`, pdf_id=1.
- Render call 2 (same template version) → `status=cached`, same pdf_id.
- PATCH template → version 1 → 2.
- Render call 3 → `status=rendered`, **new** pdf_id=2 (cache invalidated by version bump).
- `GET /pdf/cache/2` → real 197 KB PDF.
- DELETE template → 204 (cascades cache).
- Legacy `POST /pdf/report-card` → 410 Gone.

**Bug-fixes during the session:**
- WeasyPrint footer collapsing on short content → switched to `position: fixed` (Gotcha #14).
- Logo squished into square → all surfaces now use `h-X w-auto` with native 5:4 ratio.
- Wrong logo (handoff placeholder) → replaced with user-supplied PNGs from `/Users/manjeetsaini/Downloads/files/`.
- 410 branch on legacy POST shadowed `POST /pdf/templates` (router order) → registered `pdf_templates` BEFORE `pdf` (Gotcha #13).
- SQLAlchemy Enum sent Python attribute name `pseb_admit_card` instead of `.value` `pseb-admit-card`, hit MySQL "Data truncated for column 'kind'" → added `Enum(TemplateKind, values_callable=…, native_enum=False)` (Gotcha #12).
- Admin password reset to `admin123` via SSH-driven bcrypt + UPDATE (user explicitly authorised).

**Outcome:**
- Live URLs verified: `/admin/templates`, `/admin/templates/:id` (3 sections), all 6 ad-hoc PDF endpoints, `/api/pdf/templates/...` flow.
- Bundle: 866 KB JS / 267 KB gz (~+13 KB from Templates pages).
- Snapshot retained pre-deploy: `app_20260508_180215.tgz` · `db_20260508_180215.sql.gz`.

### Session 7 — 2026-05-08 (later) · iOS app scaffold + Mobile Apps page
**Focus:** Add an iOS native app parallel to `android/`, move the APK link off Login into a dedicated post-login menu page that lists both apps.

**Web changes:**
- Removed the "Download for Android" footer block from [Login.tsx](../frontend/src/pages/Login.tsx) — login is now form-only.
- New [MobileApps.tsx](../frontend/src/pages/MobileApps.tsx) at `/mobile-apps`. Two cards (Android = Available + direct APK download; iOS = Coming soon + TestFlight steps). Both list install instructions in a muted box.
- Sidebar got a new "Resources" section with a single `Smartphone`-iconed entry. Available to all roles (admin + staff). Links: [Layout.tsx](../frontend/src/components/Layout.tsx) + [App.tsx](../frontend/src/App.tsx).

**iOS app — `ios/` (new top-level project, mirrors `android/` philosophy):**
- Stack: SwiftUI + URLSession + async/await + Keychain (no third-party deps; no CocoaPods/SPM dependencies). iOS 16+, SwiftUI `NavigationStack`. Bundle id `in.expressonly.kisattendance`.
- **XcodeGen-driven:** `ios/project.yml` is the single source of truth — the `.xcodeproj` is gitignored and regenerated via `brew install xcodegen && xcodegen`. Treat it like Android's `build.gradle.kts`. Reasoning: `.pbxproj` is a UUID-laden monstrosity that nobody enjoys merging.
- Same 6 screens as Android, file-for-file: [LoginView](../ios/KisAttendance/UI/Login/LoginView.swift) (admin segmented control + staff access code), [HomeView](../ios/KisAttendance/UI/Home/HomeView.swift) (3 tiles + ⋯ menu with About + Logout), [TakeAttendanceView](../ios/KisAttendance/UI/Attendance/TakeAttendanceView.swift) (P/A/L chips, defaults to Present, save), [HistoryView](../ios/KisAttendance/UI/History/HistoryView.swift) (read-only), [StudentsListView](../ios/KisAttendance/UI/Students/StudentsListView.swift) + [StudentDetailView](../ios/KisAttendance/UI/Students/StudentDetailView.swift). Class scope read from JWT `allowed_classes`.
- [ApiClient](../ios/KisAttendance/Data/ApiClient.swift) is a singleton URLSession wrapper that mounts everything under `https://expressonly.in/school/api/`, attaches `Bearer <jwt>`, and on 401 posts `kis.authExpired` Notification → `AppRoot.onReceive` calls `session.logout()` (parallel to Android's `authExpired` SharedFlow).
- [AuthStore](../ios/KisAttendance/Data/AuthStore.swift) persists token + name + classes in Keychain (`kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`) — iOS analogue of Android's EncryptedSharedPreferences.
- Versioning mirrors Android: [version.xcconfig](../ios/version.xcconfig) holds `MARKETING_VERSION` + `CURRENT_PROJECT_VERSION`; [scripts/build-ios.sh](../ios/scripts/build-ios.sh) auto-increments the build number, runs xcodegen, archives Release, exports `.ipa` (development signing). `--no-bump` flag for rebuilds.
- README at [ios/README.md](../ios/README.md) covers setup, distribution paths (TestFlight/Ad Hoc/App Store), and arch parallels with Android.

**Distribution reality (documented for future):**
- iOS has no APK-style sideload — every install path requires Apple infrastructure ($99/yr Apple Dev Program). The Mobile Apps page accurately marks iOS as "Coming soon — TestFlight invite required" until that's set up. The build script's export plist sets `method=development`; flip it to `app-store` + use `xcrun altool` once the user has App Store Connect.
- Code signing not configured in repo — relies on Xcode's Automatic signing reading the user's signed-in Apple ID. Nothing to back up at this stage; once a distribution cert is created (Apple Dev portal), it joins the irreplaceable list alongside the Android keystore.

**Outcome:**
- Frontend type-checks clean (`tsc --noEmit` passes).
- ✅ **Deployed to TEST** via `/deploy-test-all` at 08:01 IST. Snapshot retained: `app_20260508_080042.tgz` + `db_20260508_080042.sql.gz`. Live URLs verified (SPA, `/api/health`, APK download all 200). Bundle: 745 KB JS / 235 KB gz (≈+1 KB gz).
- iOS build NOT verified — this Mac has only Command Line Tools, not full Xcode. `xcodegen` not installed either. User chose to defer iOS build (would need ~10 GB Xcode install from App Store + `brew install xcodegen`).
- ⚠️ Pending user actions: (a) install Xcode + run `cd ios && xcodegen && open KisAttendance.xcodeproj` to verify iOS source compiles, (b) decide on Apple Dev account ($99/yr) before iOS can reach phones — until then the `/mobile-apps` page accurately marks iOS as "Coming soon — TestFlight invite required".

> Session 6 (Android app + web date pickers) archived → see [SESSION_HISTORY_6.md](./SESSION_HISTORY_6.md)

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
