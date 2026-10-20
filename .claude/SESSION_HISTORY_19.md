# Session 19 — 2026-10-18 → 2026-10-19 · Results v2 to TEST, optional subjects, role dashboards, brand look, stay signed in

**Branch:** `dev` · **Prod untouched** (still `54db9cd`, schema 0013, app build 19) · **TEST** runs dev `a71d7b7`, schema **0021**, staging app **1.3.3 build 24**.
Plan file of the Results phase: `~/.claude/plans/sharded-brewing-cocoa.md` (rotates; later overwritten by the dashboards and stay-signed-in plans).

## 1. Results module v2 (plan phases 0–6)

Built before the mid-session context compaction: commits `71411f5` (results engine v2, academic sessions, report card v2, render jobs), `8569103` (web sessions + letter grades), `3373cf0` (backend hardening), `b5915f8` (refuse saves made against a stale or failed batch load: `base_batch_id`), `884cc7c` (Marks Entry menu grant enforced on the server).

Owner decisions (2026-10-18): report-card layout per template (`summary` | `components`); rank, class size and attendance computed with manual override; letter grades for grading subjects entered in Marks Entry; drafts flagged on screen and left off cards (`includeDrafts` super-admin only); house stays per-student data; DOB optional (no fabricated 2010-01-01); `pdf_templates.scope` column; co-scholastic block from grading subjects; `/marks/bulk` → 410; staff may resolve templates, write remarks/house and render/download their own classes' cards; async bulk render with progress + ZIP.

**Cross-check (2026-10-19):** 8 review lenses → 55 merged findings → 58 fix items (14 decided by the lead, 38 from review, 6 known). Highlights:
- Batch **revision** guard (migration 0018): every save/submit/approve/reject/import/cascade bumps `marks_batches.revision`; a save carrying an old `base_revision` gets 409 before any write; web and app reload untouched screens and keep unsaved edits behind a banner.
- App builds 19/20 (no `base_batch_id`) may no longer remove saved marks (409 "This version of the app can't remove saved marks…"); `GET /marks/batches` refuses an unknown session (422).
- Migration 0019 clears the v1 per-student card overrides (both v1 rows on prod/TEST had empty remarks).
- Grades null until a subject (and, overall, every subject) is complete; integer-only marks (NumberField integer mode); unsaved-change guards on pickers and tabs; CSV export flags provisional/draft numbers; the ZIP leaves out cards that changed after the run; `includeDrafts` super-admin only, Force re-render admin only; `apiError` always a string + an ErrorBoundary; the Sessions page pre-fills dates from `GET /sessions/defaults`; roster attendance equals the printed value; the PSEB admit card refuses to print without a DOB.
- Commits `d85df75` (server), `40fd943` (web), `53f518b` (app), `4c89774` (Results opens on Term 1 while Term 2 has no marks).

**Sample report cards for the principal** (made-up 8th class, rendered with the real code — skill `sample-report-cards`): the student photo never printed and WeasyPrint ignored flex `gap` (tiles, logo, grading scale touching) → fixed with fixed-size images and margins, `REPORT_CARD_TEMPLATE_REVISION = 4` (Gotcha #24). Principal approved the light design.

**UI testing on TEST** (headless Chrome; super-admin, admin and a teacher via the TEST temporary password; logins only in env vars — skill `test-verification`): Results (3 scopes, each-exam view, CSV, print), Report cards tab, Templates, Marks Entry (integer-only, unsaved-change prompt, locked-batch behaviour), Sessions pre-fill, Punjabi toggle, phone width, admin/teacher permission boundaries — all passing.

**Policy confirmed by the principal (2026-10-19):** memory `project_results_policy`. **Still awaiting the principal:** renaming mistyped exam names in 11th/12th English ("PT First", "P.T Second") — do not apply, not even on TEST.

## 2. Optional subjects (11th/12th Mathematics) — migration 0020

Request: Mathematics is an additional subject taken by ~3 students in 11th and 12th; its marks must count only for them. Rules (owner defaults, stand until the principal says otherwise): non-takers get `not_taken` (left out of total, max, percentage, grade, completeness and the report card); takers count normally; an optional subject never affects pass/promotion; rank by exact percentage; whole-number marks.
- `class_subjects.is_optional` + `subject_enrollments`; super-admin ticks takers on Class Subjects → subject (checklist, "N of M"); Marks Entry lists takers only; saves refuse marks for non-takers (422) and never prune their rows; results show "N/A".
- On TEST: 11th and 12th Mathematics are optional with **no takers ticked yet**.
- Commits `2ebe2e1` (server), `585a5ed` (web), `32e1871` (app). Verified: 12 API checks + browser check.

## 3. App theme, role dashboards and brand look

- **Theme:** the app followed the phone's dark mode with hard-coded light-mode colours (dark-grey login card, dark-blue title). Now Light is the default for every install, Settings offers Light / Dark / Same as phone, the dark palette is readable (`KisColors`), status-bar icons are white over navy top bars on every screen. Commits `63e10d8`, `134d271` (TEST app 1.3.1 build 22).
- **Classes bug:** admins carry an empty `allowed_classes`, so Take attendance / Past attendance / Students / the coverage card showed "No classes assigned" → `AuthRepository.visibleClasses` everywhere (Gotcha #21).
- **Server:** `GET /attendance/class-summary`, `GET /marks/batches/summary`; scope holes closed (a teacher with no classes saw every class's attendance total and every student; `GET /fees` without a class limited to admins and Fees-menu staff (first shipped admin-only; corrected 2026-10-20, `339c013`)); attendance CSV import onto a holiday clears the holiday flag.
- **Web dashboard:** admin "Class attendance today" pie (Marked / Pending / Holiday → class lists, `?attendance=` in the URL so Back returns) + "Class-wise attendance" bar chart for every role (Today / This week / This month; bands ≥ 90 / 75–89 / < 75 with the 75 % PSEB line; teachers see only their classes).
- **Android:** ☰ drawer; admin dashboard (classes pie → `classes-today/{kind}` list screens, students donut, class-wise bars, approvals or session & term, marks progress, fees, students & staff, notices) and teacher dashboard (my classes today, class-wise, marks to finish, results readiness, session, notices); module colour accents (`KisModule`), gradient headers with the crest, Playfair Display Bold (OFL, bundled), `KisIcons`, a Notices screen. TEST app 1.3.2 build 23. Commits `8fb38a7`, `3ef6c60`, `af44687`, `1ffe380`; roadmap `4ad7e96` ([docs/ROADMAP.md](../docs/ROADMAP.md)).
- **Data insight:** in October 2026 only 6 of 15 classes (U.K.G, 2nd, 7th, 8th, 11th, 12th) marked any attendance in the system (prod clone).

## 4. Stay signed in — migration 0021

Root cause: 1-hour access JWTs (`JWT_EXPIRY_HOURS=1` on both instances) and no server session state, so the app and the website asked for the password every hour. Owner decisions: several saved accounts per phone with a switcher, 30 days of use before the password is needed (180 days absolute), the app asks "Sign in faster next time?" after a password login, the website stays signed in with Remember me.
- Server (`b211a3e`): `device_sessions`, rotating refresh tokens with replay protection and a 60-second lost-response grace, `/auth/refresh`, `/auth/logout` (Bearer optional), `/auth/sessions`, admin `DELETE /staff/{id}/sessions`, revocation on password change/reset, temp-password clear and staff deletion, 10 failed logins per identifier per 15 min → 429; 32 new tests (first auth tests in the repo; `factories.staff()`).
- Web (`c686312`): HttpOnly cookie, bootstrap refresh before routes, single-flight refresh on 401, SSE recreated on token change, server-side logout, "session ended" note. A repeat pass found and fixed three bugs (note never shown, cookie could switch a tab's account, PC clock skew).
- Android (`6916304`, app 1.3.3 build 24 `a71d7b7`): BiometricPrompt (`BIOMETRIC_WEAK | DEVICE_CREDENTIAL`) on cold start and after 15 min in background; saved accounts (org.json in the encrypted prefs — Gotcha #16); Switch account; Logout removes the account; Settings (theme, App lock, signed-in devices); OkHttp `Authenticator`; photos load with the header instead of `?token=`.
- Verified on TEST: 11 API checks + 5 browser checks. **The fingerprint/face flow has not been run on a phone yet (owner).** Rules: Gotcha #25; design memory `project_stay_signed_in`.

## 5. TEST state and operations

- Deploys from the working copy (rsync pattern in Gotcha #23); migrations 0014–0021 all ran cleanly on the TEST prod clone; last deploy 2026-10-19 22:09.
- Every active TEST staff member has an admin-set **temporary password** (value user-known, never recorded) for teacher-view testing; `/sync-test-data` wipes it.
- TEST `.env`: `AUTH_COOKIE_PATH=/kisschool/api/auth`.
- Staging app history this session: 1.3.0 b21 (results) → 1.3.1 b22 (optional subjects + theme) → 1.3.2 b23 (dashboards) → 1.3.3 b24 (biometric).
- The server box runs in IST (`Asia/Kolkata`), so `date.today()` matches users' browsers.

## 6. Working-process lessons (Claude Code)

- A 63-agent cross-check workflow burned ~35 % of a 5-hour usage window in ~20 minutes (16 concurrent verifiers each re-reading the whole change set). The owner asked for pacing; since then ≤ 2 agents at once, agents read only the files their task names, and status is reported in % (memory `feedback_usage_pacing`).
- Workflow resume re-runs every agent call after the first edited/new one — including finished parallel siblings. It re-ran the finished website step once (harmless; it found three real bugs).
- An internet drop and a usage limit each killed an agent mid-run; resuming with "a previous agent was cut off — check what's on disk and finish" worked both times.
- A background "wait for the journal" loop never fired because the journal is compact JSON (`"type":"result"`, no spaces) — match without spaces.

## 7. Go-live — 2026-10-20

The owner tested on TEST (web on Windows Chrome, app 1.3.3 on a Xiaomi) and said "make it live, before that check test server logs … if anything need to fix".
- **Log review** (`/check-logs test 1d` + nginx's shared access log + the `device_sessions` table): no crashes or restarts. One regression — 10 `GET/POST /fees` 403s from staff #4, who holds the Fees menu on TEST *and prod*: last night's scope fix had made unscoped `GET /fees` admin-only. Fixed to "admins + Fees-menu staff see every class; other teachers only their classes" (recording/deleting payments stay admin-only, as on prod); test rewritten; verified with the real accounts on TEST; `339c013`.
- **App sign-in** at 09:32 forced a password because the phone still held a sign-in from the pre-1.3.3 app (no saved sign-in); from 09:40 the saved sign-in renewed (rotations at 09:41 and 10:23) and switching staff #4 ↔ #22 worked without a password. Not a bug.
- **Prod pre-flight:** schema 0013, healthy; `CORS_ORIGINS=https://kisschool.in` already set; no 11th/12th Mathematics marks; no fee payments recorded yet.
- **Deploy 11:33:** `backup-db.sh` → `~/Downloads/db-backups/school_prod_20261020_113300.sql.gz` (62 MB); `git archive` of `339c013` + `echo "DEPLOY PROD" | deploy-all.sh`; snapshot `20261020_113317`; migrations 0014→0021 clean; healthy. Smoke on prod (as user `school`, `http://127.0.0.1:8000/api`): 26/26. The three tracebacks `/check-logs prod` listed were from 2026-05-30 (fixed `notify_student_edit_request` NameError) — the section isn't time-filtered.
- **Data:** 11th and 12th Mathematics set optional on prod via the API (no takers ticked → nobody can enter Mathematics marks there until the super-admin ticks them).
- **Prod app:** built 1.3.4 build 25 (61 DTO classes intact), owner chose "Upload now" at 11:35 on a school day → uploaded and verified (4,387,781 bytes); every teacher is force-updated on next open.
- Docs: CLAUDE.md + memory marked live (`3042946`); [docs/ROADMAP.md](../docs/ROADMAP.md) refreshed with a "Waiting on the school" table and the go-live follow-ups (`2e8fc0d`).

---

## Appendix — the CLAUDE.md Status table as it stood before the Session 19 condensation

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
| Test deploy | ✅ Live at http://69.62.72.137/kisschool/admin/ (second instance on the prod box since 2026-10-19; prod logins) |
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
| LogRecord `name` collision bug (Session 9) | ✅ Fixed — see Gotcha #12. Was crashing student-create + delete responses for ~8 days |
| **Dual-mode navigation (Session 12)** | ✅ Top-bar mode (default) with 5 section dropdowns + Sidebar mode (legacy). Hamburger toggles modes on desktop, opens drawer on mobile. `useNavMode` persists choice to `localStorage`. Logout button + user-menu dropdown live in slim topbar. Sidebar/TopNav/Layout split into 3 components consuming a shared `SECTIONS` registry at [lib/nav-sections.ts](../frontend/src/lib/nav-sections.ts) |
| **Class Subjects master + per-subject exam-component editor (Session 13)** | ✅ Migration 0008; super-admin CRUD at `/class-subjects` + spreadsheet-style component editor at `/class-subjects/:id`; "Seed KIS default pattern" one-click materialises 127 subjects + 654 components from the school's exam-pattern sheet across Nursery–12th. Bulk CSV import, category enum, FK CASCADE on component delete |
| **MarksEntry master-bound + per-student validation + roll/parent display (Session 13)** | ✅ Dropdowns bind to class_subjects + subject_exam_components, max marks auto-filled read-only. Server enforces `0 ≤ marks ≤ max_marks` on `POST /marks/bulk` + bulk-import. Student rows show `<roll>  <name>  · S/o <father>` sorted by roll# numerically — disambiguates duplicate names |
| **Marks draft → submit → lock → edit-request workflow (Session 13)** | ✅ Migration 0009; new `marks_batches` + `marks_edit_requests`. 3-state MarksEntry (New/Draft → Submitted+locked → Submitted+pending). Tabbed `/edit-requests` (Student edits / Marks edits) with auto-switch to non-empty queue. Approve flips batch back to draft (no timer); required reason on request; new shadcn `Tabs` primitive |
| **NumberField + global spinner removal + hard-clamp (Session 13)** | ✅ [components/ui/number-field.tsx](../frontend/src/components/ui/number-field.tsx) stores state as string (empty allowed), rejects keystrokes that exceed `max`/`min`, red border on invalid. Spinner arrows hidden globally on `<Input type="number">` — kills the "100 → 31" bug (Gotcha #13) |
| **Auto cache-bust on deploy (Session 13)** | ✅ Vite injects `__BUILD_ID__` + emits `dist/version.json`; `useVersionCheck()` polls every 5 min while visible and reloads with `?_v=<ts>` query bust on mismatch. nginx serves `index.html` + `version.json` with `Cache-Control: no-cache, must-revalidate`. No more "need a hard refresh after deploy" (Gotcha #15) |
| **Attendance half-day / holiday / clear-day + in-app approvals (Session 17)** | ✅ Migration 0012 widens `attendance_records.status` ENUM to add `H` + adds `attendance.is_holiday`; `PUT /attendance` takes `is_holiday`, new `DELETE /attendance?class=&date=`, `marked-dates` returns `{dates, holidays}`. Android gained a super-admin `ApprovalsScreen` (student-edit / marks-edit / deletion queues) and became role-aware. Shipped in APK v1.2.4 build 17; current APK **v1.2.5 build 18** |
| **Term-scoped result aggregation (Session 18)** | ✅ **Live on prod** (verified 2026-10-19: prod DB at 0013, `services/results.py` deployed). Migration 0013 adds `subject_exam_components.term` (1/2/NULL=both), widens `marks.exam_type` 60→80, adds `pdf_cache.source_hash`. New [app/services/results.py](../backend/app/services/results.py) is the single roll-up engine behind both `GET /api/marks/results` and the report-card PDF builder. MarksResults page rebuilt around class+session+scope; ClassSubjectDetail gained a Term column |
| **"All" class-sentinel expansion (Session 18)** | ✅ **Live on prod** (verified 2026-10-19: `constants.py` with `expand_classes` deployed). New [app/constants.py](../backend/app/constants.py) expands the `staff_classes` `"All"` sentinel into the real 15-class list at login AND on token decode, so clients stop seeing a literal `"All"` and `assert_class_allowed` stops rejecting real class names (Gotcha #21) |
| **TEST re-homed onto the prod box (2026-10-19)** | ✅ Second instance at http://69.62.72.137/kisschool/admin/ provisioned by the now knob-driven scripts (own user/dir/unit :8001/DB, one include line in the enamfoss vhost); runs dev HEAD `8569103` (schema 0017); data cloned from prod by `/sync-test-data` (row counts identical, 0013→0017 migrated cleanly); staging APK v1.2.7 build 20 points at it. Prod + enamfoss verified unchanged (Gotcha #23) |

---
