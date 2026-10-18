# 08 · Risks, Limitations and Improvements

> Index: [README.md](README.md) · Previous: [07-design-patterns-and-tradeoffs.md](07-design-patterns-and-tradeoffs.md) · Next: [09-onboarding-guide.md](09-onboarding-guide.md)

Every item below was verified against the working tree at commit `8645bdd` on
2026-10-18. Severity: **Critical / High / Medium / Low**. Effort: **S** (hours),
**M** (a day or two), **L** (a week or more). Numbers are stable identifiers for
referencing items from commits and CLAUDE.md.

## A. Security

| # | Finding | Evidence | Severity | Effort |
|---|---|---|---|---|
| **A1** | **The Android release keystore and its passwords are committed.** `android/keystore.zip` is tracked (added in the root commit `307b7fc`, 2026-05-16) and contains `keystore/kis-release.jks` and `keystore/keystore.properties`. `.gitignore` covers `android/keystore/*.jks` and `keystore.properties` but not the zip. Anyone with read access to the repository can sign an APK that installs over the real app on every teacher's phone. CLAUDE.md Gotcha 2 calls this key "irreplaceable". | `git ls-files android/keystore.zip`; `unzip -l android/keystore.zip` | **Critical** | M |
| A2 | **A database root password is written in a tracked file.** `.claude/GOTCHAS_13_21.md` item 20 records the TEST box's MySQL root password in plain text. | that file, tracked | **High** | S |
| A3 | **Operational credentials in documentation and scripts.** `.claude/CLAUDE.md` names the admin login identifiers and a default password in its header; `backend/scripts/fix_staff_credentials.py` (tracked) hardcodes a uniform staff password and an email domain used to fabricate addresses; `backend/app/config.py` ships default admin passwords that are the live seed on first boot. | those files | **High** | S |
| A4 | **No rate limiting or lockout on authentication.** `POST /auth/login` and `POST /auth/forgot-password` accept unlimited attempts. Staff initial passwords are 6 random digits (`routers/staff.py::_gen_password`, 900,000 possibilities) and temp passwords never expire. bcrypt slows each attempt but nothing stops an online guess. CLAUDE.md lists this as "optional later". | `routers/auth.py`, `routers/staff.py` | **High** | S–M |
| A5 | **JWTs travel in query strings** for SSE (`/stream/*?token=`), inline documents (`/files/.../inline?token=`) and cached PDFs (`/pdf/cache/{id}/inline?token=`). They are therefore written to nginx access logs and browser history. Tokens cannot be revoked; logout is client-side only. | `deps.current_user_sse`, `frontend/src/lib/api.ts::fileUrl`, `lib/pdf.ts` | Medium | M |
| A6 | **Authorisation gaps behind UI-only gates.** `GET /pdf/cache/{id}` has no ownership or class check (any authenticated user can enumerate cached report cards). `GET /fees` returns every school fee to staff unless a `class` filter is sent. `POST /pdf/{kind}` lets any staff member render salary slips or letterheads. `POST /notices` is open to all roles. The portal hides these behind `allowed_menus`, but the API is the real boundary. | `routers/pdf_templates.py::_serve_cache_row`, `routers/fees.py::list_fees`, `routers/pdf.py`, `routers/notices.py` | Medium | S each |
| A7 | **Server-side validation is weaker than the CSV import.** `POST /students` and `PATCH /students/{id}` accept any `phone`, `aadhar` and `class_name` (only `bulk-import` checks 10/12 digits); `class_name` is never validated against `CLASSES` anywhere in the API, so a typo creates an orphan class invisible to every picker; `session` is free text. | `schemas/student.py`, `routers/students.py` | Medium | S |
| A8 | `CORSMiddleware` is configured with `allow_credentials=True`; with the dev default `CORS_ORIGINS=*` that is the permissive combination. Production sets a real origin. | `main.py` | Low | S |
| A9 | Secrets hygiene is otherwise good: `.env` generated on the server with 600 permissions, bcrypt everywhere, reset tokens stored hashed and single-use, generic forgot-password response. | `scripts/provision/04-write-env.sh`, `security.py`, `routers/auth.py` | — | — |

**Remediation for A1 (do first):**
1. Establish whether the GitHub repository has ever been public or shared
   (**UNKNOWN / needs owner confirmation**).
2. Remove the file from the tree, purge it from history (`git filter-repo --path android/keystore.zip --invert-paths`), force-push both branches, and ask GitHub support to clear cached views. Add `android/*.zip` and `*.jks` to `.gitignore`.
3. If exposure cannot be ruled out, treat the key as compromised: generate a new keystore, and plan a **one-time uninstall/reinstall** for every teacher, because Android refuses to upgrade an app whose signing key changed. The force-update gate (`UpdateGate.kt`) can display the instruction, but it cannot perform the migration.
4. Store the keystore and `keystore.properties` only in the owner's password manager / offline backup, as Gotcha 2 already prescribes.

## B. Reliability and operations

| # | Finding | Evidence | Severity | Effort |
|---|---|---|---|---|
| B1 | **Realtime events reach only part of the audience.** The SSE broker is per process and gunicorn runs two workers, so a browser connected to worker A never hears about writes handled by worker B. CLAUDE.md still says "single uvicorn worker". | `deploy/school-management.service` (`-w 2`), `events.py`, `.claude/GOTCHAS_1_6.md` item 1 | Medium | S (`-w 1`) / M (Redis) |
| B2 | **Bulk PDF rendering is synchronous inside one request.** `POST /pdf/templates/{id}/render` loops WeasyPrint over every requested student; a large class can exceed gunicorn's `--timeout 120`, which kills the worker (502 for everyone on it). nginx's 24 h read timeout will not save it. | `routers/pdf_templates.py::render_bulk`, `pdf/render_or_cache.py`, the unit file | Medium | M (client-side chunking is S) |
| B3 | **No scheduled database backup.** Snapshots are taken only during deploys (`remote_snapshot`) and by the manual `backup-db.sh`; they stay on the same disk, pruned after 30 days. A disk failure loses everything. | `scripts/deploy/common/lib.sh` | High | S (cron + off-box copy) |
| B4 | **Rollback restores code, not schema.** `remote_rollback` replaces `app/` from the tarball but never reverses `alembic upgrade head`. Safe today only because every migration is additive. | `lib.sh::remote_rollback` | Medium | — (keep migrations additive; document) |
| B5 | `scripts/deploy/prod/` has **no `rollback.sh`**; the TEST one has hardcoded `/school/api/health`. | directory listing | Low | S |
| B6 | **Unbounded growth of blobs.** `pdf_cache` keeps every superseded `(template_version, source_hash)` row forever; `student_documents` stores originals uploaded from Android without compression. Both inflate `mysqldump` time and disk. | `pdf/render_or_cache.py` (no delete path), `android/.../util/ImagePick.kt` vs `frontend/src/lib/compress.ts` | Medium | S (cleanup job) |
| B7 | **No monitoring or alerting.** Health is checked only at deploy time; there is no uptime check, disk alert or error-rate alert on either box, both of which are shared with other applications. | `scripts/`, absence of any monitor | Medium | S (external uptime monitor) |
| B8 | Hard purge (`DELETE /admin/deletion-requests/{kind}/{id}`) cascades to marks, fees, attendance and documents with no export; by design, but irreversible. | `routers/deletion_requests.py::purge`, FK `CASCADE` | Low | S (export before purge) |
| B9 | **Migration 0013 is committed but not deployed**, and its `term` back-fill by name pattern can leave hand-renamed components as `NULL` (counted in both terms). | CLAUDE.md Next Steps 0–1, `alembic/versions/0013_component_term.py` | Medium | S (deploy + audit query) |

## C. Correctness defects found during analysis

| # | Finding | Evidence | Severity | Effort |
|---|---|---|---|---|
| C1 | **"Marks submitted" emails are never sent.** `notify_marks_submitted` is imported by `routers/marks_batches.py` but `submit_batch` never calls it. | grep shows the only call sites are the definition and the import | Low (feature silently missing) | S |
| C2 | **Reports ignore soft delete.** `GET /reports/class-wise` and `/staff-list` include archived rows; `/attendance-monthly` counts half-days (`H`) as leave while `/attendance/today-summary` counts them separately. | `routers/reports.py` | Medium | S |
| C3 | **N+1 and a hard ceiling on the students list.** `_to_out` issues three `COUNT` queries per student (document flags); the Dashboard requests `page_size=1000`, so one dashboard load can run ~3,000 queries, and the server caps `page_size` at 1000 — a school with more students is silently truncated. The Dashboard also downloads the full fee and notice lists to compute KPIs. | `routers/students.py::_to_out`, `frontend/src/pages/Dashboard.tsx` | Medium | S (one aggregated query) / M (summary endpoint) |
| C4 | **Lost-update window in edit approval.** `_apply_diff` writes the request's `new` values without checking that the row still holds the `old` values; a super-admin edit made in between is overwritten. | `routers/edit_requests.py::_apply_diff` | Low | S |
| C5 | Results include draft marks with no indication of batch status (teachers cannot tell what is unsubmitted); legacy rows with non-component `exam_type` are silently ignored. Documented as Next Step 4. | `routers/marks.py::class_results` | Low | S |
| C6 | `datetime.utcnow()` (19 call sites) is deprecated in Python 3.12 and mixes with the timezone-aware timestamps in `security.py`. | grep | Low | M (coordinated change) |
| C7 | Phone login falls back to scanning every staff row in Python when the indexed match fails. Fine for one school; O(n) per failed attempt. | `routers/auth.py::login` | Low | S (store normalised phone) |
| C8 | `deploy/.env.example` repeats the SMTP block and one comment gives PROD's `APP_BASE_URL` without `/admin`. | that file | Low | S |

## D. Maintainability and drift

| # | Finding | Evidence | Severity | Effort |
|---|---|---|---|---|
| D1 | **Hand-mirrored registries with no guard.** Class list in three languages (`backend/app/constants.py`, `frontend/src/lib/utils.ts`, `android/.../StudentForm.kt`); menu keys in two (`permissions.py`, `lib/menus.ts`); grade bands in `services/results.py` and as static text in `pdf/templates/report-card.html.j2`; API shapes in Pydantic, `types/api.ts` and Kotlin DTOs. | those files | Medium | M (`/api/meta` endpoint for classes + menus; generate `types/api.ts` from OpenAPI) |
| D2 | **No automated tests** despite pytest being configured and installed. | `backend/pyproject.toml`, missing `backend/tests/` | High | M to start |
| D3 | **Dead code and unused dependencies**: `apscheduler`, `httpx`, `python-dotenv` installed but never imported; `Settings.STATIC_DIR` / `BACKUP_DIR` unused; the static-mount block at the bottom of `main.py`; `notify_marks_submitted` (C1). | grep | Low | S |
| D4 | **Committed build artefacts**: `frontend/vite.config.js`, `vite.config.d.ts`, `tsconfig.tsbuildinfo`, `tsconfig.node.tsbuildinfo`. A stale `vite.config.js` is actively dangerous (Gotcha 17). | `git ls-files frontend/` | Medium | S (ignore them; `npm run build` regenerates) |
| D5 | **Stale documentation**: root `README.md` (Firebase/GitHub Pages era); `STATUS.md` (2026-05-08); `ios/README.md` says the app talks to the TEST API while `ApiClient.swift` points at production; `android/README.md` predates flavours; `deploy/nginx.public-site.conf` references an old domain; `packages/design-system/README.md` cites a CI script `frontend/scripts/check-i18n.mjs` that does not exist; CLAUDE.md's repo layout shows the old Android package path, says JWTs last 8 h while the default is 1 h, and lists admin emails that differ from the constants in `routers/auth.py`. | those files | Medium | S each |
| D6 | **iOS app is far behind and inconsistent**: Session 7 feature set only, hardcoded production URL, bundle id `in.expressonly.kisattendance` versus Android's `in.kisschool`, no update gate. | `ios/` | Low (not distributed) | L |
| D7 | Frontend bundle ~965 KB (293 KB gzipped) with no route-level code splitting; Chart.js is about half. | CLAUDE.md Next Step 13 | Low | S–M |
| D8 | Bilingual coverage is partial; new MarksResults controls are English literals. | `frontend/src/pages/MarksResults.tsx` | Low | M |
| D9 | The one cross-router import (`edit_requests.py` → `students.py` helpers) will grow into a tangle if a third consumer appears. | `routers/edit_requests.py` | Low | S (move to `services/`) |

## E. Scalability ceilings (as built)

| Dimension | Current limit | Where it comes from |
|---|---|---|
| Students in a class picker | 500 per request | `page_size: 500` in `Attendance.tsx`, `MarksEntry.tsx`, `Fees.tsx` |
| Students on the Dashboard | 1,000 | `page_size: 1000` in `Dashboard.tsx`, `le=1000` in `routers/students.py` |
| SSE subscribers per channel per worker | unbounded connections, but each queue drops events beyond 100 unread | `events.py` |
| Concurrent long requests | 2 workers × the uvicorn thread pool; a PDF bulk render holds one thread for its whole duration | unit file, `render_bulk` |
| Request duration | 120 s before gunicorn kills the worker | `--timeout 120` |
| Upload size | 25 MB | nginx `client_max_body_size` |
| Database size | one MySQL instance on a shared VPS; documents and PDFs as `LONGBLOB` | `models/document.py`, `models/pdf_template.py` |
| Availability | single box, no failover, shared with unrelated services | infrastructure |

None of these matter for one school of a few hundred students today; C3 is the one
that will be felt first.

## F. Ranked improvement plan

| Order | Item(s) | Value | Effort | Why this order |
|---|---|---|---|---|
| 1 | A1 keystore removal + exposure assessment | prevents the one failure that cannot be undone later | M | irreversible if exploited |
| 2 | A2, A3 rotate and scrub credentials; make `fix_staff_credentials.py` read its password from the environment | closes known leaks | S | cheap, high value |
| 3 | B3 nightly `mysqldump` + off-box copy; B7 external uptime check on `/api/health` | survives a disk failure; notices outages | S | cheap insurance |
| 4 | B9 deploy migration 0013 (`/deploy-test-all` → verify → `/deploy-prod-all`), run the `term IS NULL` audit from CLAUDE.md | unblocks Session 18 work | S | already written |
| 5 | A4 rate limit `/auth/*` (nginx `limit_req` or a FastAPI limiter) and expire temp passwords | hardens the weakest credential class | S–M | — |
| 6 | A6, A7 close the API-level gaps: cache-row class check, fees scoping, `class_name ∈ CLASSES` and phone/Aadhaar validators in Pydantic | aligns API with the UI's promises | S | small, contained |
| 7 | C3 aggregate document flags in one query; add a dashboard summary endpoint | removes the first real performance cliff | S–M | — |
| 8 | B1 decide: `-w 1` now (simplest, adequate load) or Redis later | makes realtime deterministic | S | one-line change if `-w 1` |
| 9 | D2 first tests: `services/results.py`, `pdf/builder.py`, `_bulk.parse_date_field`, `constants.expand_classes`, then the permission matrix with `TestClient` | protects the logic that already caused incidents | M | highest regression value per test |
| 10 | C1, C2, C4, C8 small correctness fixes | — | S | batch them |
| 11 | D4 untrack build artefacts; D3 remove dead code and dependencies | removes a known footgun | S | — |
| 12 | D5 documentation refresh (root README, iOS README, CLAUDE.md facts) | stops misleading newcomers | S | do alongside 1–2 |
| 13 | D1 `/api/meta` for classes and menus; generate `types/api.ts` from OpenAPI | ends silent drift | M | — |
| 14 | B2 async bulk render with progress over SSE (or render in client-side chunks as a stop-gap) | removes the timeout risk at scale | M–L | matches CLAUDE.md Next Step 14 |
| 15 | B6 cache cleanup job; Android image downscale | bounded growth | S | — |
| 16 | D7 code splitting; D8 bilingual completion; D6 iOS catch-up | polish | M–L | after the above |

> Next: [09-onboarding-guide.md](09-onboarding-guide.md) — how to start working on all this safely.
