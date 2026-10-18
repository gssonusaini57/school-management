# 07 · Design Patterns and Trade-offs

> Index: [README.md](README.md) · Previous: [06-configuration-and-environment.md](06-configuration-and-environment.md) · Next: [08-risks-limitations-and-improvements.md](08-risks-limitations-and-improvements.md)

## 1. Patterns actually in use

| Pattern | Where | What it buys | What it costs |
|---|---|---|---|
| **Router-owns-the-rule** (no service layer) | every file in `backend/app/routers/` | fewest files to read for one feature; handler reads top-to-bottom | rules are duplicated when two routers need them (soft-delete visibility, uniqueness) and are hard to unit-test without HTTP |
| **Pure engine for anything printed and displayed** | `services/results.py`, `pdf/builder.py` | the table and the report card cannot disagree; testable without a DB | callers must pre-load rows and pass them in |
| **Dependency-injected identity** | `deps.py` (`current_user`, `require_admin`, `require_super_admin`, `assert_class_allowed`) | authorisation is declarative and uniform | staff class scope must be asserted *inside* handlers that take a class — forgetting it is the most likely security slip |
| **Approval queue** (request → super-admin review) | `student_edit_requests`, `marks_edit_requests`, the `status` state machine for deletions | audit trail with reasons; destructive actions need two people | three parallel implementations that must evolve together; lookups by display name, not id |
| **Soft delete as a state machine** | `models/record_status.py`, `students.status`, `staff.status` | recoverable deletes, purge as an explicit second step | every list query must remember the `!= deleted` filter (`reports.py` forgot) |
| **Publish-after-commit + client invalidation** | `events.py`, `routers/stream.py`, `frontend/src/lib/sse.ts` | the server never pushes data, only "something changed"; cache logic stays in TanStack Query | per-process broker; dropped events when a queue is full; requires nginx buffering off |
| **Sentinel expansion at the boundary** | `constants.expand_classes` at login and on decode | one row means "all classes" without 15 rows; old tokens are repaired on the fly | every consumer of `allowed_classes` must receive concrete names; the sentinel string must never leak again |
| **Dual credential** | `staff.temp_password_hash` | an admin can act for an absent teacher without resetting their password | temp passwords never expire; both hashes are checked on every staff login |
| **Content-hash cache key** | `pdf_cache.source_hash` in `pdf/render_or_cache.py` | marks or data edits invalidate cached PDFs without a version bump | render inputs are loaded even on a hit; old cache rows are never deleted |
| **Nullable FK + composite UNIQUE = free upsert and legacy tolerance** | `marks.batch_id`, `UNIQUE(batch_id, student_id)` | the batch workflow shipped without back-filling old marks; re-saves update instead of duplicating | relies on MySQL treating NULLs as distinct in unique indexes — not portable to PostgreSQL |
| **Atomic bulk import with structured errors** | `routers/_bulk.py`, every `bulk-import` endpoint, `BulkImportDialog.tsx` | the admin fixes the sheet once and re-uploads; no half-imported files | large files are validated row-by-row in Python with per-row DB checks |
| **Never-raises side effects** | `notifications.py::_never_raises` | a mail or template bug can never turn a committed write into a 500 | failures are only visible in logs |
| **Structured logging with request context** | `logging_config.py`, `middleware.py`, `app.audit.*` loggers | every line carries `request_id`, `user_sub`, `user_role`; `X-Request-ID` ties client reports to log lines | `extra=` keys must avoid Python's reserved `LogRecord` names |
| **Hand-mirrored registries** | `CLASSES` ×3 (Python/TS/Kotlin), `MENU_KEYS` ×2, grade bands in `results.py` + the static text in `report-card.html.j2`, Pydantic schemas ↔ `types/api.ts` ↔ Kotlin DTOs | no code generation toolchain | drift is silent until a user hits it |
| **Build-time base path** | `VITE_BASE`, `SITE_BASE_PATH`, `import.meta.env.BASE_URL` everywhere | one tree deploys to a sub-path and to an apex domain | every URL in the SPA must be derived, never hardcoded |
| **Build-id cache busting** | `__BUILD_ID__`, `dist/version.json`, `useVersionCheck`, nginx `no-cache` on the shell | no "please hard-refresh" support calls | three pieces (Vite, runtime, nginx) must all be in place |
| **Design tokens as single source** | `packages/design-system/`, copies in `backend/app/pdf/assets/tokens.css` and the handoff | portal, public site and PDFs share one palette and typography | copies must be refreshed together |
| **Owned UI primitives** | `frontend/src/components/ui/` (shadcn), `NumberField`, `DatePicker` | bugs are fixed once (spinner "100 → 31", native date picker traps) | you maintain the primitives yourself |
| **Manual DI on mobile** | `android/.../di/AppContainer.kt` | tiny APK, no annotation processing | wiring is by hand |
| **Fail-open update gate** | `UpdateGate.kt`, `AppUpdateRepository.fetch()` returns `null` on error | a dead manifest URL can never lock teachers out | an old build keeps working if the manifest is unreachable |

## 2. Coding conventions

* **API shape**: snake_case JSON everywhere except PDF payloads, which use the handoff's
  camelCase via Pydantic aliases (`class_` ↔ `class`, `rollNo`, `fatherName`). Lists are
  bare arrays except `GET /students` (page envelope) and the queues (`{items: [...]}`).
* **Query parameters**: the class filter is always `?class=` (aliased to `class_name`
  in Python because `class` is a keyword).
* **Audit fields** record display names (`added_by`, `updated_by`, `saved_by`,
  `requested_by`, `reviewed_by`), not ids. Log events use `event="snake_case_verb"` plus
  domain keys (`student_id`, `class_name`, `actor`, `reason`).
* **Enums** are `str` enums persisted as `VARCHAR` with `values_callable`.
* **Dates**: ISO on the wire; display as `DD MMM YYYY`, PSEB documents `DD-MM-YYYY`;
  CSV import accepts Indian spreadsheet formats.
* **Money**: `Decimal(10,2)` in MySQL, string or number on the wire, Indian grouping on display.
* **Commits**: conventional-commit style (`feat(results): …`, `fix(auth): …`,
  `chore(android): …`, `docs(memory): …`); no AI attribution trailers (enforced by
  `.githooks/` and `.claude/settings.json`); branch `dev`, default `master`.
* **Frontend**: pages own their data (`useQuery`/`useMutation`/`useSSE`); URL search
  params are the source of truth for list filters and pagination (`Students.tsx`);
  bounded numeric inputs use `NumberField`; dates use `DatePicker`; translations go
  through `t()` / `<T k>` with keys under `portal.*`, both `en` and `pa`.
* **Documentation**: every non-obvious decision is recorded as a numbered "Gotcha" in
  `.claude/CLAUDE.md` and rotated into `GOTCHAS_*.md` archives; `/save-session`
  maintains it.

## 3. Error-handling strategy

* Expected failures are `HTTPException`s with human-readable `detail` strings (often
  naming the conflicting record) so the UI can toast them verbatim via `apiError()`.
* Range errors on marks return a `detail` **object** (`{message, rows}`) listing the first
  ten offenders.
* Bulk imports never raise for row problems; they return `inserted: 0` plus the error list.
* Unexpected failures become a generic 500 with the traceback in `app.error.log`,
  found by `request_id`.
* Side effects after commit cannot fail the request (notifications) or are kept trivially
  safe (logging keys).
* The frontend treats any 401 as "session over" and redirects to login; Android does the same via the OkHttp interceptor.

## 4. Logging, metrics and monitoring

| Layer | What exists | Where |
|---|---|---|
| Application logs | JSON lines with `ts`, `level`, `logger`, `msg`, `request_id`, `user_sub`, `user_role` + event fields; `app.log` (all) and `app.error.log` (WARNING+), 10 MB × 5 rotation | `backend/app/logging_config.py`, `/opt/school-management/logs/` |
| Access logs | one line per request with `status` and `duration_ms` from the middleware; plus gunicorn's own `access.log` / `error.log` | `middleware.py`, `deploy/school-management.service` |
| Audit trail | WARNING-level events for every approval-workflow transition (`student_delete_requested`, `marks_batch_submitted`, `student_edit_approved`, …) so they land in `app.error.log` too | routers |
| Health | `GET /api/health` → `{"status": "ok"}`; used by `health_wait` after every deploy | `routers/health.py`, `scripts/deploy/common/lib.sh` |
| Operator tooling | `/check-logs [30m|2h|1d]` streams six sections (service status, journalctl, error tail, tracebacks, access tail, 4xx/5xx) read-only; `download-logs.sh` for offline analysis | `scripts/deploy/*/check-logs.sh` |
| Metrics / alerting / uptime monitoring | **none** | — |

## 5. Testing strategy

There is **no automated test suite**. `backend/pyproject.toml` configures pytest for a
`tests/` directory that does not exist, and `requirements.txt` installs `pytest`,
`pytest-asyncio` and `httpx` (the FastAPI test client's transport) — the scaffolding
was prepared and never used. What stands in for tests today:

1. `scripts/deploy/common/lib.sh::local_python_lint` — `ast.parse` of every backend file (catches syntax errors only).
2. `npm run build` (`tsc -b`) — type-checks the frontend; `types/api.ts` is the de-facto contract test with the backend.
3. Manual verification on TEST before `/deploy-prod-*`, with snapshots and automatic rollback on failed health checks.
4. The Gotcha list, which is effectively a regression-test suite written in prose.

Where tests would pay off first (see 08): `services/results.py` and `pdf/builder.py`
(pure functions), `_bulk.py::parse_date_field`, `constants.expand_classes`, the
permission matrix via FastAPI's `TestClient` against a SQLite or disposable MySQL schema.

## 6. Deliberate trade-offs — what looks old and why it must stay (for now)

| Looks odd | Why it exists | What depends on it |
|---|---|---|
| `POST /marks/bulk`, `GET /marks?class=&exam_type=`, `POST /marks/bulk-import` next to the batch workflow | the free-text marks path predates the class-subjects master; CSV import still writes it | existing rows with `batch_id IS NULL`; removing the endpoints is safe only after a back-fill (CLAUDE.md Next Step 5) |
| `POST /pdf/{kind}` catch-all returning 410 for two kinds | the ad-hoc endpoint was the original PDF API; two kinds moved to templates | router registration order in `main.py` (the specific routers must be mounted first) |
| `pdf_templates.term_key` duplicating `term` with `NULL → ""` | MySQL cannot put a `COALESCE` in a unique constraint | the uniqueness of `(kind, class, session, term)` templates and per-student data |
| `staff_classes` row with the literal `"All"` | the staff bulk import and the frontend collapse "every class" to one row | expansion in two places (`auth.login`, `deps._parse`); do not "fix" the data without removing both expansions |
| `marks.exam_type` storing a *component name* | the column predates components; renaming it would touch every client | `services/results.py` matching rule `marks.exam_type == component_name` |
| Hyphenated enum values (`report-card`) in a `VARCHAR` | the handoff's document kinds are hyphenated and appear in URLs | `values_callable` on every such column (Gotcha 8) |
| Committed `frontend/vite.config.js` and `*.tsbuildinfo` | by-product of `tsc -b` with project references | nothing depends on them being tracked; see 08 |
| `_handoff/` proposing Next.js / React Native / React-PDF while the repo uses Eleventy / Kotlin / WeasyPrint | the agency package is the *design* source of truth; the stacks were re-decided for hosting and distribution reasons | tokens, strings and JSON schemas are still read from it at build time |
| No-cache `<meta http-equiv>` tags in `frontend/index.html` | carried over from the GitHub Pages era | harmless; the real mechanism is nginx + `version.json` |
| `STATUS.md` and the root `README.md` describing older states | snapshots that were never retired | nothing; candidates for cleanup |
| `main.py` static-mount block | from the Firebase single-file era when FastAPI might have served `index.html` | nothing; dead code |
| Display names as audit actors | the first version had no user ids for admin roles | `notifications._staff_email_by_name` resolves requesters by name |
| `datetime.utcnow()` naive timestamps throughout | MySQL `DATETIME` columns are naive; consistency with existing rows | everything that compares `expires_at`, `requested_at` etc.; switching to aware datetimes is a coordinated change |

## 7. Trade-offs the team made explicitly (and their current cost)

| Choice | Benefit | Cost today |
|---|---|---|
| Synchronous everything (no worker, no queue) | zero infrastructure | bulk PDF render for a large class risks gunicorn's 120 s timeout |
| Files in MySQL | one backup, one store | `mysqldump` grows with every document; large exports are slow |
| Two gunicorn workers with an in-memory broker | resilience to one worker crashing | ~half of realtime events do not reach a given browser |
| JWT without server-side revocation | stateless | a stolen token is valid until expiry; logout is client-side |
| Tokens in query strings for SSE and inline files | works with `EventSource` and `<img>` | tokens appear in nginx access logs |
| Hand-mirrored registries | no codegen | drift risk (three class lists, two menu registries) |
| Manual testing | speed of a solo developer | regressions are caught by users |

> Next: [08-risks-limitations-and-improvements.md](08-risks-limitations-and-improvements.md) — the ranked list of what to do about all this.
