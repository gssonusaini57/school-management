# 02 · High-Level Architecture

> Index: [README.md](README.md) · Previous: [01-domain-concepts.md](01-domain-concepts.md) · Next: [03-folder-structure-guide.md](03-folder-structure-guide.md)

## Architectural style

A **modular monolith behind nginx**:

* one Python process group (FastAPI under gunicorn/uvicorn) exposes a REST API plus
  Server-Sent Events, renders PDFs and sends email;
* one MySQL schema is the only persistent store, including binary documents and
  cached PDFs;
* three clients consume the API: a React SPA, a native Android app, an iOS scaffold;
* a separately built static marketing site shares the same nginx server block.

There is no message queue, no cache server, no object storage, no background worker.
The modules inside the backend are organised by domain (one router + schema + model
per entity) rather than by technical layer, with a thin shared core
(`deps`, `security`, `events`, `logging_config`).

## Component diagram

```
                      TEACHER PHONE                    ADMIN / TEACHER BROWSER                PUBLIC VISITOR
                 ┌────────────────────┐          ┌────────────────────────────┐          ┌──────────────────┐
                 │ Android app        │          │ React SPA (frontend/)      │          │ any browser      │
                 │ android/ (Kotlin,  │          │ TanStack Query + axios     │          │                  │
                 │ Compose, Retrofit) │          │ EventSource for SSE        │          │                  │
                 └─────────┬──────────┘          └──────────┬─────────────────┘          └────────┬─────────┘
                           │ HTTPS JSON (Bearer JWT)        │ HTTPS JSON (Bearer) + SSE (?token=)    │ HTTPS
                           ▼                                ▼                                       ▼
            ┌────────────────────────────────────────────────────────────────────────────────────────────────┐
            │ nginx  (deploy/nginx.school.conf on TEST · deploy/nginx.kisschool.conf on PROD)                 │
            │   /api/*        → proxy 127.0.0.1:8000  (buffering off, 24h read timeout for SSE, 25m uploads)  │
            │   /admin/*      → alias frontend/dist  (SPA fallback to index.html; no-cache on index+version)  │
            │   /downloads/*  → alias frontend/dist/downloads (APK + version manifest)                        │
            │   /*            → root public-site/dist (Eleventy static, /en/ and /pa/)                        │
            └───────────────────────────────────────┬────────────────────────────────────────────────────────┘
                                                    │ HTTP
                                                    ▼
            ┌────────────────────────────────────────────────────────────────────────────────────────────────┐
            │ systemd school-management.service → gunicorn -w 2 -k UvicornWorker  (backend/app/main.py)      │
            │                                                                                                │
            │  RequestContextMiddleware ─▶ CORS ─▶ routers (/api/*)                                           │
            │  ┌──────────┐ ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ ┌────────────┐   │
            │  │ auth     │ │ students    │ │ attendance   │ │ marks        │ │ fees      │ │ staff      │…  │
            │  └──────────┘ └─────────────┘ └──────────────┘ └──────────────┘ └───────────┘ └────────────┘   │
            │        │ deps.py (JWT → CurrentUser, require_admin, assert_class_allowed)                       │
            │        │ schemas/ (Pydantic in/out)   models/ (SQLAlchemy)   services/results.py (pure)         │
            │        │ events.py in-process Broker ──▶ routers/stream.py (sse-starlette)                      │
            │        │ pdf/ (Jinja2 → WeasyPrint)   notifications.py → mailer.py (smtplib, Zoho)               │
            └────────┼───────────────────────────────────────────────────────────┬───────────────────────────┘
                     │ SQLAlchemy 2 / PyMySQL (pool 10+5, pre-ping)              │ SMTP 465 SSL
                     ▼                                                           ▼
            ┌─────────────────────────────────┐                        ┌──────────────────┐
            │ MySQL 8  schema school_management│                        │ Zoho Mail        │
            │ 20 tables · LONGBLOB documents   │                        │ (outbound only)  │
            │ Alembic versions 0001 … 0013     │                        └──────────────────┘
            └─────────────────────────────────┘
```

## Components and responsibilities

| Component | Location | Responsibility | Talks to |
|---|---|---|---|
| API server | `backend/app/` | authentication, authorisation, validation, all business rules, persistence, realtime fan-out, PDF rendering, email | MySQL, SMTP |
| Database | MySQL schema `school_management` (migrations in `backend/alembic/versions/`) | the single source of truth, including files (`student_documents.data`, `pdf_cache.data` as `LONGBLOB`) | — |
| Staff portal | `frontend/` (Vite build → `frontend/dist/`) | all admin/teacher UI; owns no business rules beyond form validation and display | API over HTTPS |
| Public site | `public-site/` (Eleventy build → `public-site/dist/`) | marketing pages in `en` and `pa`; purely static | nothing at runtime |
| Design system | `packages/design-system/` | tokens, Tailwind preset, i18n JSON, brand assets shared by portal, public site and PDFs | imported at build time |
| Android app | `android/` | teacher workflows on phones: attendance, students, marks entry, approvals | API over HTTPS |
| iOS app | `ios/` | same intent as Android, far behind in features; not distributed | API over HTTPS |
| Reverse proxy | `deploy/nginx.*.conf` | TLS, path routing, SPA fallback, cache headers, static downloads | gunicorn |
| Process manager | `deploy/school-management.service` | runs gunicorn as user `school`, restarts on failure, loads `.env` | — |
| Deploy tooling | `scripts/` | provision a server, build, rsync, migrate, restart, health-check, snapshot, roll back | SSH to servers |

## How the pieces communicate

| From → To | Protocol | Auth | Notes |
|---|---|---|---|
| SPA → API | HTTPS JSON via axios (`frontend/src/lib/api.ts`) | `Authorization: Bearer <JWT>` from `sessionStorage` | 401 clears the token and redirects to the base-relative login page |
| SPA → API (SSE) | `EventSource` to `GET /api/stream/{channel}?token=` (`frontend/src/lib/sse.ts`) | JWT in the query string, because `EventSource` cannot set headers | one connection per channel per page; nginx must not buffer |
| SPA → API (images, PDFs for `<img>`/`<a download>`) | `GET …/inline?token=` (`routers/files.py`, `routers/pdf_templates.py`) | JWT in the query string | same reason |
| Android → API | Retrofit + OkHttp (`android/.../di/AppContainer.kt`) | Bearer header added by an interceptor; 401 clears the store and emits `authExpired` | base URL per flavour from `BuildConfig` |
| iOS → API | `URLSession` (`ios/KisAttendance/Data/ApiClient.swift`) | Bearer; 401 posts a notification | base URL hardcoded to production |
| Router → Router | in-process Python imports | — | only `routers/edit_requests.py` imports helpers from `routers/students.py` |
| Router → Browser (realtime) | `events.Broker.publish` → per-subscriber `asyncio.Queue` → SSE | — | in-memory, per worker process |
| Router → Email | `notifications.py` → `mailer.send_email` (stdlib `smtplib`) | SMTP app password from `.env` | best-effort, after commit, never raises |
| API → MySQL | SQLAlchemy 2.0 ORM, synchronous sessions per request (`db.get_db`) | DB user `school` | pool 10 + 5 overflow, `pool_pre_ping`, recycle 1200 s |
| Deploy host → servers | SSH + rsync (`scripts/deploy/common/lib.sh`) | per-environment SSH key named in `scripts/deploy/{test,prod}/env.sh` | snapshots to `/opt/school-management/backups/` |

## Two deployment layouts from one source

```
 TEST  (shared host expressonly.in)                 PROD  (dedicated domain kisschool.in)
 ───────────────────────────────────                ───────────────────────────────────────
 https://expressonly.in/school/           public    https://kisschool.in/
 https://expressonly.in/school/admin/     SPA       https://kisschool.in/admin/
 https://expressonly.in/school/api/       API       https://kisschool.in/api/
 https://expressonly.in/school/downloads/ APK       https://kisschool.in/downloads/
 nginx: snippet included in an existing             nginx: standalone server {} with its own
        server {} (deploy/nginx.school.conf)               Let's Encrypt cert (deploy/nginx.kisschool.conf)
 VITE_BASE=/school/admin/  VITE_API_URL=/school/api VITE_BASE=/admin/  VITE_API_URL=/api
 SITE_BASE_PATH=/school                             SITE_BASE_PATH=""  (apex root)
 Android flavour: staging (in.kisschool.test)       Android flavour: prod (in.kisschool)
```

Both servers run the identical backend; the prefix is stripped by nginx
(`proxy_pass http://127.0.0.1:8000/api/`), so FastAPI always sees `/api/...`. The
frontend derives everything (router basename, login redirect, `version.json` URL) from
`import.meta.env.BASE_URL`, so one knob — `VITE_BASE` — flips the layout. See
[06-configuration-and-environment.md](06-configuration-and-environment.md).

## Cross-cutting mechanisms (where to look)

| Concern | Mechanism | Code |
|---|---|---|
| Authentication | HS256 JWT, 1 hour by default (`JWT_EXPIRY_HOURS`), claims `sub`, `role`, `name`, `allowed_classes`, `allowed_menus` | `backend/app/security.py`, `routers/auth.py` |
| Authorisation | three dependency functions (`current_user`, `require_admin`, `require_super_admin`) + a class-scope assertion + menu grants checked client-side | `backend/app/deps.py`, `permissions.py`; `frontend/src/components/ProtectedRoute.tsx`, `lib/nav-sections.ts` |
| Validation | Pydantic request models; DB `UNIQUE` constraints as the race-safe backstop; pre-flight uniqueness checks for friendly 409s | `backend/app/schemas/`, `routers/students.py::_check_uniqueness` |
| Realtime | publish-after-commit → SSE → TanStack `invalidateQueries` | `events.py`, `routers/stream.py`, `frontend/src/lib/sse.ts` |
| Caching | TanStack `staleTime` 30 s; server `pdf_cache` keyed by template version **and** a content hash of marks + student data; browser cache busting via `__BUILD_ID__` + `version.json` + nginx `no-cache` on `index.html` | `frontend/src/main.tsx`, `backend/app/pdf/render_or_cache.py`, `frontend/vite.config.ts`, `lib/version.ts` |
| Soft delete | `status` enum on `students` and `staff`; default queries filter `!= deleted` | `models/record_status.py` |
| Observability | JSON logs with `request_id`, `user_sub`, `user_role` injected via `contextvars`; `X-Request-ID` response header; gunicorn access/error logs; `/api/health` | `logging_config.py`, `middleware.py`, `routers/health.py` |
| Email | stdlib SMTP to Zoho; templates as inline-styled HTML tables | `mailer.py`, `email_templates.py`, `notifications.py` |
| Print | Jinja2 templates + shared brand CSS → WeasyPrint → bytes | `backend/app/pdf/` |
| i18n | i18next in the SPA, a Nunjucks `t` filter in the public site, `Bilingual{en,pa}` objects in PDFs; all strings from `packages/design-system/i18n/` and the handoff `strings.json` | `frontend/src/lib/i18n.ts`, `public-site/eleventy.config.cjs` |

## Why this architecture (reconstructed rationale)

| Decision | Why it was made | Evidence |
|---|---|---|
| FastAPI + MySQL on the existing VPS | the owner already ran MySQL and nginx for the sister project `uploadmytds`; zero new infrastructure, one more systemd unit | `.claude/memory/project_shared_vps.md`, `scripts/provision/` |
| Files as `LONGBLOB` rows | no object storage to provision or back up separately; one `mysqldump` captures everything; nginx caps uploads at 25 MB and the client compresses images to ~900 px | `backend/app/models/document.py`, `frontend/src/lib/compress.ts`, `.claude/GOTCHAS_7_12.md` item 10 |
| SSE instead of WebSockets or polling | the UI only needs "something changed, refetch"; `EventSource` reconnects by itself and passes through nginx with buffering off | `events.py`, `deploy/nginx.school.conf` |
| In-process broker, no Redis | a single school has a handful of concurrent users; the limitation (events only reach subscribers of the worker that handled the write) was accepted knowingly | `.claude/GOTCHAS_1_6.md` item 1 |
| WeasyPrint in Python rather than the handoff's React-PDF | the marks and student rows live server-side; rendering next to the data avoids shipping it to a browser; the brand CSS could be reused almost verbatim | `backend/app/pdf/render.py`, `_handoff/.../CLAUDE.md` (proposes React-PDF) |
| Eleventy static site rather than the handoff's Next.js | nothing dynamic on the public site; static HTML needs no Node runtime on the server and is trivially cached | `public-site/eleventy.config.cjs` |
| Native Kotlin/Compose app rather than React Native | ~3–6 MB APK side-loaded from the school's own URL, no Play Store; force-update gate keeps old builds off the API | `android/README.md`, `android/.../ui/update/UpdateGate.kt` |
| JWT in `sessionStorage` | the token dies with the tab; "remember me" only keeps the identifier in `localStorage` | `frontend/src/lib/api.ts` |
| Base-path parametrisation | TEST had to live under `/school/` on a shared host, PROD got a dedicated domain later; one source tree for both | `frontend/vite.config.ts`, `scripts/deploy/*/env.sh` |
| Approval queues instead of direct edits for admin/staff | the super-admin wanted a review step for destructive or sensitive changes made by others | `routers/edit_requests.py`, `deletion_requests.py`, `marks_batches.py` docstrings |

## How it evolved

| Session (date) | Change | Why it matters today |
|---|---|---|
| 1–2 (May 2026) | Firebase single-file app | explains `_archive/index.firebase.html` and the no-cache meta tags still in `frontend/index.html` |
| 3 | FastAPI + MySQL + React rewrite | the current foundation |
| 4 | provisioning + deploy framework, TEST live | `scripts/provision/`, `scripts/deploy/` |
| 5 | form validation, atomic CSV bulk import | `routers/_bulk.py`, `BulkImportDialog.tsx` |
| 6 | Android app, popover date pickers | `android/`, `components/ui/date-picker.tsx` |
| 7 | iOS scaffold, Mobile Apps page | `ios/`, `pages/MobileApps.tsx` |
| 8 | brand design system, public site, WeasyPrint PDFs, templated bulk PDFs | `packages/design-system/`, `public-site/`, `backend/app/pdf/`, migration 0002 |
| 9 | soft delete + super-admin role | migration 0003, `record_status.py` |
| 10–11 | staff email/phone + password auth, employee IDs, menu grants | migrations 0005, 0006 |
| 12 | top-bar navigation | `components/TopNav.tsx`, `lib/nav-sections.ts` |
| 13 | class-subjects master, marks batches + edit requests, NumberField, build-id cache bust | migrations 0008, 0009 |
| 14–15 | Android force-update gate, dashboard calendar | `UpdateGate.kt`, `GET /attendance/marked-dates` |
| 16 | PROD on kisschool.in, Android rebrand to `in.kisschool`, temp passwords, forgot-password email | migrations 0010, 0011, `deploy/nginx.kisschool.conf` |
| 17 | half-day / holiday attendance, Android approvals screen | migration 0012 |
| 18 | term-scoped results engine, marks-aware PDF cache, "All" sentinel expansion | migration 0013, `services/results.py`, `constants.py` — **not yet deployed** |

Detailed narratives: `.claude/SESSION_HISTORY_*.md` and the Session History section of `.claude/CLAUDE.md`.

## Tensions to keep in mind

* Realtime assumes one process; gunicorn runs two (see [08](08-risks-limitations-and-improvements.md)).
* Everything is synchronous: a bulk render of many report cards runs inside one HTTP request.
* Registries are mirrored by hand across Python, TypeScript and Kotlin.
* The repo documents intent exhaustively in `.claude/` but has no executable tests.

> Next: [03-folder-structure-guide.md](03-folder-structure-guide.md) — every folder and what it is for.
