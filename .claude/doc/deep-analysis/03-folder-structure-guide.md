# 03 · Folder Structure Guide

> Index: [README.md](README.md) · Previous: [02-high-level-architecture.md](02-high-level-architecture.md) · Next: [04-core-modules-and-business-logic.md](04-core-modules-and-business-logic.md)

Every tracked folder in the repository, grouped by area. Generated folders
(`node_modules/`, `dist/`, `.venv/`, `build/`, `.gradle/`, `.kotlin/`, `.idea/`,
`__pycache__/`) are listed once at the end: never commit them and never edit inside them.

```
school-management/
├── .claude/            AI-assistant project memory, slash commands, skills, this knowledge base
├── .githooks/          commit-msg guard against AI attribution trailers
├── _archive/           the retired Firebase single-file app (read-only)
├── _handoff/           brand agency design package (read-only source of truth for tokens/strings/schemas)
├── android/            Kotlin + Jetpack Compose teacher app
├── backend/            FastAPI application, Alembic migrations, PDF pipeline
├── deploy/             server config templates: nginx, systemd, .env example
├── frontend/           React + Vite staff portal
├── ios/                SwiftUI teacher app scaffold (XcodeGen)
├── packages/           design-system shared by portal, public site and PDFs
├── public-site/        Eleventy + Tailwind static marketing site (en + pa)
├── scripts/            provisioning, deploy, Android build tooling
├── README.md           STALE (Firebase era) — see 08
├── STATUS.md           design-integration report frozen 2026-05-08
└── .gitignore
```

## Repository root files

| Path | Why it exists | Don't change casually |
|---|---|---|
| `README.md` | the original project README from the Firebase era; still advertises GitHub Pages and access codes | rewrite it, but do so deliberately — it is the first thing GitHub shows |
| `STATUS.md` | Sprint report for the design-system integration, dated 2026-05-08 | treat as history; the live status is `.claude/CLAUDE.md` |
| `.gitignore` | ignores secrets (`.env`, `android/keystore/*.jks`, `keystore.properties`, `local.properties`), build output, logs, local Claude settings | adding a pattern that matches `frontend/public/downloads/*.apk` or `app-version*.json` is already done on purpose — the APK is a build artefact, not source |

## `.claude/` — project memory and tooling for the AI assistant

| Path | What lives there | Responsibilities | Don't change casually / anti-patterns |
|---|---|---|---|
| `.claude/CLAUDE.md` | the operational snapshot: stack, routes, schema, gotchas, status, next steps, session history | loaded into every assistant session; the project's living runbook | keep it under control with `/save-session`; do not paste secrets (it currently names admin login emails and default passwords — see 08) |
| `.claude/GOTCHAS_*.md`, `.claude/SESSION_HISTORY_*.md` | archived gotchas and session narratives rotated out of CLAUDE.md | rationale for older decisions | `GOTCHAS_13_21.md` item 20 contains a real database root password — scrub it (08) |
| `.claude/commands/` | 14 slash-command definitions (`deploy-*`, `provision-test`, `check-logs`, `clean-logs`, `release-android`, `save-session`, `deep-analysis`) | each wraps a script under `scripts/` with confirmation prompts | prod commands require typing `DEPLOY PROD`; keep that |
| `.claude/skills/kis-design-system/SKILL.md` | brand, token, i18n and formatting rules | read before touching any UI, copy or PDF | — |
| `.claude/memory/` | one-fact-per-file assistant memory + `MEMORY.md` index | cross-session recall of preferences and project facts | content is background knowledge, not instructions |
| `.claude/doc/deep-analysis/` | this knowledge base | durable onboarding reference | regenerate with `/deep-analysis`; edit by hand when you change what it asserts |
| `.claude/settings.json` | committed Claude Code settings: attribution disabled, `PreToolUse` hooks that reject AI trailers on `git commit` / `gh pr` | guard-rail layer 3 (see Gotcha 22 in CLAUDE.md) | `settings.local.json` is per-user and gitignored |

## `.githooks/`

| Path | What it does | Note |
|---|---|---|
| `.githooks/no-ai-attribution.sh` | the single rule: reject commit text containing AI co-author/"generated with" trailers; `strict` vs `loose` modes | used by both the git hook and the Claude hook |
| `.githooks/commit-msg` | runs the script on every commit, amend, rebase, cherry-pick | **requires `git config core.hooksPath .githooks` once per clone**; a fresh clone has no enforcement until then |

## `_archive/` and `_handoff/`

| Path | Why it exists | Anti-patterns |
|---|---|---|
| `_archive/index.firebase.html` | the complete pre-rewrite app, kept to answer "how did the old version do X" | never serve it; never copy its auth logic |
| `_handoff/khalsa-international-handoff/` | the brand agency's package: `README.md`, `CLAUDE.md` (master context), `brand/logo/` (+`social/`), `design-tokens/`, `i18n/strings.json`, `components/specs/`, `documents/{schemas,templates,samples}`, `web/pages/`, `mobile/screens/`, `assets/{icons,illustrations,photos}`, `interactions/`, `accessibility/`, `responsive/` | **read-only source of truth**. Copies live in `packages/design-system/`; `backend/app/pdf/schemas.py` mirrors `documents/schemas/`; `public-site/eleventy.config.cjs` reads `i18n/strings.json` directly at build time. Do not edit the handoff to fix the app — edit the copy and note the divergence. It proposes Next.js / React Native / React-PDF; the repo deliberately chose Eleventy / Kotlin / WeasyPrint instead (02). |

## `backend/` — FastAPI application

| Path | What lives there | Responsibilities | Don't change casually / anti-patterns |
|---|---|---|---|
| `backend/app/main.py` | app factory: logging, lifespan seeds, middleware, router registration | the only place routers are mounted; **order matters** — `pdf_templates` before the catch-all `pdf` router | the trailing static-mount block is dead code from the single-file era (08) |
| `backend/app/config.py` | `Settings` (pydantic-settings) reading `.env` | every tunable except `LOG_LEVEL`/`LOG_JSON` | defaults are dev-only; production values come from `/opt/school-management/.env` |
| `backend/app/db.py` | engine, `SessionLocal`, `Base`, `get_db` | one synchronous session per request | never call `Base.metadata.create_all()`; schema changes go through Alembic |
| `backend/app/security.py` | bcrypt hashing, JWT encode/decode, reset-token hashing | — | HS256 with `JWT_SECRET`; rotating the secret logs everyone out |
| `backend/app/deps.py` | `CurrentUser`, `current_user`, `current_user_sse`, `require_admin`, `require_super_admin`, `assert_class_allowed`, `db_dep` | the authorisation vocabulary every router uses | new endpoints must take one of these dependencies; `health` is the only unauthenticated route |
| `backend/app/constants.py` | canonical `CLASSES`, `expand_classes`, `is_all_sentinel` | the "All" sentinel expansion | mirrored in `frontend/src/lib/utils.ts` and `android/.../StudentForm.kt` — change all three |
| `backend/app/permissions.py` | `MENU_KEYS`, `DEFAULT_STAFF_MENUS`, `sanitize_menus` | staff menu grants | mirrored in `frontend/src/lib/menus.ts` |
| `backend/app/events.py` | in-memory `Broker` | SSE fan-out | per-process; see 08 before adding workers |
| `backend/app/logging_config.py`, `middleware.py` | JSON logging with request context; `RequestContextMiddleware` | observability | never pass reserved `LogRecord` keys (`name`, `module`, …) in `extra=` — it raises after the commit (Gotcha 12) |
| `backend/app/mailer.py`, `email_templates.py`, `notifications.py` | SMTP send, inline-styled HTML templates, fail-safe workflow notifications | transactional email | every notification helper is wrapped in `@_never_raises`; call them **after** `db.commit()` |
| `backend/app/models/` | one SQLAlchemy model module per entity (`admin`, `staff`, `student`, `document`, `attendance`, `marks`, `marks_batch`, `fee`, `notice`, `class_subject`, `pdf_template`, `student_edit_request`, `password_reset`, `record_status`) | table definitions, constraints, enums | a new model must also be imported in `backend/alembic/env.py` or autogenerate will not see it; hyphenated enums need `values_callable` (Gotcha 8) |
| `backend/app/schemas/` | Pydantic request/response models per entity | validation and serialisation contracts; `frontend/src/types/api.ts` mirrors them | change a response schema → change `types/api.ts` and the Android DTO in the same commit |
| `backend/app/routers/` | one router per domain + `_bulk.py` shared CSV helpers | HTTP handlers; all business rules live here (there is no service layer except `services/results.py`) | keep the `(validate → mutate → commit → publish → notify → log)` order; `_bulk.py` imports must be atomic (`inserted: 0` on any row error) |
| `backend/app/services/results.py` | pure result aggregation engine + grade bands | shared by the results API and the report-card builder | **no DB access in this module** — routers fetch rows and pass them in |
| `backend/app/pdf/` | `schemas.py` (payload models), `builder.py` (merge template + student + marks), `render.py` (Jinja2 → WeasyPrint), `render_or_cache.py` (cache-aware render), `format.py` (INR/date filters) | the whole print pipeline | `builder.py` is pure; `render_or_cache.py` is the only PDF module allowed to touch the DB |
| `backend/app/pdf/templates/` | `_base.html.j2` brand frame + one `.html.j2` per kind | layout | footers must stay `position: fixed` (Gotcha 10); crest PNG is 5:4, never force square (Gotcha 11) |
| `backend/app/pdf/assets/` | `crest-512.png`, `tokens.css` (mirror of the design-system tokens) | WeasyPrint resolves these via `file://` URIs | keep `tokens.css` in sync with `packages/design-system/tokens.css` |
| `backend/app/seed/exam_pattern.py` | 127 subjects / 654 components seed data | `POST /class-subjects/seed-defaults` | values are hand-derived from a handwritten sheet; refusing to re-seed over existing rows is intentional |
| `backend/alembic/` + `versions/` | `env.py` (loads `Settings.DATABASE_URL`, imports all models), `0001`…`0013` | schema evolution | linear chain, one head; the deploy script runs `alembic upgrade head` on every backend deploy |
| `backend/scripts/fix_staff_credentials.py` | one-shot maintenance script run on the server | repaired placeholder staff credentials and class-name spellings | contains a hardcoded default password — see 08 |
| `backend/logs/` | local log output when running the backend from this folder | — | gitignored; the server logs to `/opt/school-management/logs/` |
| `backend/requirements.txt`, `pyproject.toml`, `alembic.ini` | pinned dependencies; pytest config pointing at a `tests/` folder that does not exist | — | `apscheduler`, `httpx`, `python-dotenv` are installed but unused (08) |

## `frontend/` — React staff portal

| Path | What lives there | Responsibilities | Don't change casually / anti-patterns |
|---|---|---|---|
| `frontend/index.html` | SPA shell with Google Fonts preconnects and a `%BASE_URL%` favicon placeholder | — | the placeholder is substituted by a Vite plugin; a plain relative favicon 404s on deep links |
| `frontend/vite.config.ts` | base path from `VITE_BASE`, `__BUILD_ID__` define, `version.json` emitter, `/api` dev proxy to `:8000` | build contract | **`vite.config.js`, `vite.config.d.ts` and `*.tsbuildinfo` are committed `tsc` artefacts**; a bare `vite build` picks the stale `.js` — always `npm run build` (Gotcha 17) |
| `frontend/tailwind.config.ts`, `postcss.config.js`, `components.json` | Tailwind with the KIS preset + shadcn HSL aliases; shadcn CLI config | styling | tokens come from `packages/design-system/`; no raw hex in components |
| `frontend/.env.development`, `.env.production` | `VITE_API_URL` defaults (`/api`, `/school/api`) | — | deploy scripts override via the shell; PROD uses `/api` |
| `frontend/public/` | copied verbatim into `dist/`: `crest-mark.png`, `brand/crest-mark.png`, `downloads/` (APK + `app-version*.json`, gitignored) | static assets and the APK distribution channel | a frontend deploy without a prior APK build deletes the APK on the server (`rsync --delete`, Gotcha 4) |
| `frontend/src/main.tsx`, `App.tsx` | QueryClient (staleTime 30 s), `BrowserRouter` with base-derived `basename`, route table with guards, `useVersionCheck()` | composition root | `useBlocker` cannot be used with `BrowserRouter` (memory note `feedback_useblocker_data_router`) |
| `frontend/src/components/` | `Layout` (slim topbar + nav-mode switch), `Sidebar`, `TopNav`, `ProtectedRoute`, `T`/`BilingualHeading`, `LocaleSwitch`, `BulkImportDialog`, `ChangePasswordDialog` | app chrome and shared dialogs | menu items live in `lib/nav-sections.ts`, not in `Layout.tsx` |
| `frontend/src/components/ui/` | shadcn primitives (button, input, select, dialog, table, tabs, toast, popover, calendar, `date-picker`, `number-field`, …) | owned source, edit freely | never `npm install` shadcn; never reintroduce `<Input type="date">` or raw bounded `<input type="number">` |
| `frontend/src/lib/` | `api.ts` (axios + 401 redirect + `fileUrl`), `auth.ts` (sessionStorage user, `useAuth`, `canAccessMenu`), `sse.ts`, `version.ts`, `menus.ts`, `nav-sections.ts`, `nav-mode.ts`, `i18n.ts`, `pdf.ts`, `templates.ts` (CSV templates), `utils.ts` (`CLASSES`, formatting), `format.ts`, `compress.ts`, `student-labels.ts` | all non-visual client logic | `CLASSES` and `MENU_KEYS` are mirrors of backend registries |
| `frontend/src/pages/` | 23 route components (`Login`, `ForgotPassword`, `ResetPassword`, `Dashboard`, `Admissions`, `Students`, `StudentDetail`, `Attendance`, `MarksEntry`, `MarksResults`, `Fees`, `Notices`, `Staff`, `Reports`, `Letterheads`, `SalarySlips`, `Templates`, `TemplateDetail`, `DeletionRequests`, `EditRequests`, `ClassSubjects`, `ClassSubjectDetail`, `MobileApps`) | screens; each owns its queries, mutations and `useSSE` subscriptions | pages talk to the API only through `lib/api.ts` |
| `frontend/src/styles/globals.css` | Tailwind layers + shadcn HSL variables remapped onto KIS colours | theme bridge | change colours in tokens, not here |
| `frontend/src/types/api.ts` | TypeScript mirror of the Pydantic schemas | compile-time contract | update together with `backend/app/schemas/` |

## `public-site/` — Eleventy marketing site

| Path | What lives there | Responsibilities | Note |
|---|---|---|---|
| `public-site/eleventy.config.cjs` | loads handoff `strings.json`, deep-merges `i18n/extra-strings.json`, defines the `t`, `isCurrent`, `flipLocale` filters, passthrough-copies brand assets | build configuration | `t(key, lang)` falls back to `en`, then to `[key]` so missing strings are visible |
| `public-site/i18n/extra-strings.json` | page copy not in the handoff, same `{ns: {key: {en, pa}}}` shape | local additions | every key needs both `en` and `pa` |
| `public-site/src/_data/site.cjs` | `basePath` from `SITE_BASE_PATH` (default `/school`), nav order, footer columns, brand asset URLs | site-wide config | an explicit empty `SITE_BASE_PATH` (PROD apex) is honoured — the script uses `??`, not `||` |
| `public-site/src/_includes/` | `base.njk` (html shell, hreflang pair, fonts), `header.njk`, `footer.njk`, `pages/*.njk` (one partial per page, shared by both locales) | layout and content | page content lives in the partials, not in the locale folders |
| `public-site/src/en/`, `public-site/src/pa/` | one thin `.njk` per page (`index`, `about`, `academics`, `admissions`, `career`, `contact`, `gallery`, `notices`, `parent-portal`) + a directory data file (`en.json` / `pa.json`) setting `lang` and `layout` | locale routing (`/en/...`, `/pa/...`) | add a page in **both** folders |
| `public-site/src/index.njk` | root redirect: `localStorage` `kis.locale`, else browser language → `/en/` or `/pa/` | locale selection | — |
| `public-site/src/css/site.css` | Tailwind input | — | compiled by Tailwind CLI into `dist/css/site.css` before Eleventy runs |
| `public-site/tailwind.config.cjs`, `postcss.config.cjs`, `package.json` | KIS preset; `build` = CSS then HTML | — | — |

## `packages/design-system/`

| Path | What lives there | Note |
|---|---|---|
| `tokens.css` | CSS custom properties (colours, fonts, spacing, radius, shadow, motion) | generated from the handoff; "do not edit by hand"; mirrored to `backend/app/pdf/assets/tokens.css` |
| `tailwind.preset.cjs` | Tailwind preset consumed by `frontend/` and `public-site/` | — |
| `i18n/en.json`, `pa.json` | handoff strings split per locale (`common`, `web`, `mobile`) | regenerated by the script in the README |
| `i18n/portal-en.json`, `portal-pa.json` | staff-portal strings under the `portal` namespace | every new key in both files |
| `brand/` | crest and wordmark SVG + PNG | PNG crest is 5:4 landscape |
| `README.md` | consumption instructions | references a CI check `frontend/scripts/check-i18n.mjs` that **does not exist** (08) |

## `android/` — Kotlin/Compose teacher app

| Path | What lives there | Responsibilities | Don't change casually / anti-patterns |
|---|---|---|---|
| `android/version.properties` | `versionCode`, `versionName` | single source of the app version | `scripts/build-android.sh` bumps both on every release build; do not hardcode versions in Gradle |
| `android/app/build.gradle.kts` | flavours `prod` / `staging`, `BuildConfig.API_BASE_URL` + `APP_VERSION_URL`, signing from `keystore/keystore.properties`, R8 enabled | build definition | flavour names starting with `test` are forbidden by AGP — hence `staging` with `.test` suffix |
| `android/app/proguard-rules.pro` | keep rules for Gson DTOs (`in.kisschool.data.api.dto.**`) | release-build correctness | a package rename without updating this rule silently breaks every API call in release builds (Gotcha 16) |
| `android/app/src/main/AndroidManifest.xml` | `INTERNET` permission only, `FileProvider` for camera capture, `allowBackup=false` | — | — |
| `android/app/src/main/java/in/kisschool/` | package root (`in` is a Kotlin keyword → backtick-escaped in source) | — | — |
| `…/data/api/ApiService.kt`, `…/data/api/dto/` | Retrofit interface; Gson DTOs mirroring `backend/app/schemas/` | HTTP contract | `GET /students` returns a page envelope — use `StudentPageDto` (Gotcha 18) |
| `…/data/auth/TokenStore.kt` | `EncryptedSharedPreferences` for JWT, name, classes, role, force-change flag | credential storage | — |
| `…/data/repo/` | `AuthRepository`, `StudentRepository`, `AttendanceRepository`, `MarksRepository`, `AdminRepository`, `AppUpdateRepository` | thin wrappers over `ApiService` | `AppUpdateRepository.fetch()` returns `null` on any failure — the update gate must fail open |
| `…/di/AppContainer.kt` | manual dependency container: OkHttp with auth interceptor + 401 → `authExpired`, Retrofit, repositories | composition root | no Hilt on purpose (APK size) |
| `…/ui/nav/AppNav.kt` | `Routes` constants and the `NavHost` | navigation | — |
| `…/ui/screens/<feature>/` | `login`, `home`, `dashboard`, `attendance`, `history`, `students`, `studentdetail`, `studentedit`, `marks`, `approvals` — each a Screen + ViewModel | features | the class list copy is in `studentedit/StudentForm.kt` |
| `…/ui/update/UpdateGate.kt` | force/optional update overlay driven by `app-version.json` | gate | — |
| `…/ui/theme/`, `…/ui/components/`, `…/util/ImagePick.kt` | Material 3 theme in KIS colours; shared composables; camera/gallery pick with EXIF-correct JPEG re-encode | — | — |
| `android/app/src/main/res/` | `values/` (colours, strings, themes — `Theme.Material3.*` needs the Material Components dependency, Gotcha 5), `xml/` (`network_security_config`, `file_paths`, `data_extraction_rules`), `mipmap-anydpi-v26/` adaptive icons, `drawable-*dpi/` bitmaps | resources | — |
| `android/keystore/` | gitignored `kis-release.jks` + `keystore.properties` | release signing | **irreplaceable** (Gotcha 2) — and note `android/keystore.zip` *is* tracked; see 08 finding #1 |
| `android/gradle/wrapper/`, `gradlew`, `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties` | Gradle wrapper and root build | — | — |
| `android/README.md` | build, sign, side-load instructions | — | still names the TEST API as "the" backend; flavours supersede that |

## `ios/` — SwiftUI scaffold

| Path | What lives there | Note |
|---|---|---|
| `ios/project.yml` | XcodeGen project definition (bundle id `in.expressonly.kisattendance`, iOS 16) | **the `.xcodeproj` is generated and not committed** — edit `project.yml`, run `xcodegen` |
| `ios/version.xcconfig` | `MARKETING_VERSION`, `CURRENT_PROJECT_VERSION` | bumped by `ios/scripts/build-ios.sh` |
| `ios/KisAttendance/App/` | `@main` entry | — |
| `ios/KisAttendance/Data/` | `ApiClient.swift` (URLSession, base URL **hardcoded** to production), `AuthStore.swift` (Keychain), `Models.swift` | — |
| `ios/KisAttendance/UI/` | `AppRoot.swift` + `Login/` (Login, ChangePassword, ForgotPassword), `Home/`, `Attendance/`, `History/`, `Students/` | screens frozen at Session 7 feature level |
| `ios/KisAttendance/Resources/` | `Info.plist`, asset catalogue (accent colour, app icon) | — |
| `ios/README.md` | setup and distribution options | says it talks to the TEST API; the code points at PROD (08) |

## `deploy/` — server configuration templates

| Path | What it is | Applies to |
|---|---|---|
| `deploy/nginx.school.conf` | location snippet for the `/school/...` layout, included in the existing `expressonly.in` server block | TEST |
| `deploy/nginx.kisschool.conf` | complete HTTPS vhost at the apex | PROD |
| `deploy/nginx.public-site.conf` | **template** with two patterns for hosting the public site; references an old domain name | historical; superseded by the two files above |
| `deploy/school-management.service` | systemd unit: gunicorn, 2 workers, user `school`, `EnvironmentFile=/opt/school-management/.env` | both |
| `deploy/.env.example` | every backend setting with placeholders (SMTP block appears twice — harmless duplication) | both |

## `scripts/` — operations tooling

| Path | What it does | Note |
|---|---|---|
| `scripts/provision/provision.sh` + `00-common.sh` … `06-install-nginx-snippet.sh` | idempotent one-time server bootstrap: prerequisites, `school` user and `/opt/school-management/` tree, MySQL DB/user, `.env` (secrets generated **on the server**), systemd unit, nginx snippet | re-running is safe (Gotcha 21 in the archive); step 06 inserts the include with brace-depth parsing because the host config has `}server {` on one line |
| `scripts/deploy/common/lib.sh` | shared functions: lint (AST parse), build (Vite / Eleventy), snapshot (`app_<ts>.tgz` + `db_<ts>.sql.gz`), rsync, remote pip + `alembic upgrade head` + restart, health wait, rollback | the real deploy logic; test and prod scripts are thin wrappers |
| `scripts/deploy/test/`, `scripts/deploy/prod/` | `env.sh` (server, key, domain, path knobs) + `deploy-all.sh`, `deploy-backend.sh`, `deploy-frontend.sh`, `deploy-public-site.sh`, `backup-db.sh`, `check-logs.sh`, `download-logs.sh`, `upload-apk.sh`; **`rollback.sh` exists only under `test/`** | prod wrappers demand the literal confirmation `DEPLOY PROD` |
| `scripts/build-android.sh` | bumps version, builds the signed flavour APK, copies it to `frontend/public/downloads/`, writes the force-update manifest | the manifest sets `min_version_code == latest` — every release is a forced update unless you lower it by hand |
| `scripts/gen_android_icon.py` | generates launcher icon assets from the crest | — |
| `scripts/README.md` | one-page cheat-sheet | — |

## Generated folders (never commit, never edit)

`frontend/node_modules/`, `frontend/dist/`, `public-site/node_modules/`,
`public-site/dist/`, `backend/.venv/`, `backend/**/__pycache__/`, `android/app/build/`,
`android/.gradle/`, `android/.kotlin/`, `android/.idea/`, `ios/build/`,
`ios/KisAttendance.xcodeproj/`, `logs_backup_*/` (local log downloads). All are covered
by `.gitignore` except that `android/keystore.zip` and the `frontend/*.tsbuildinfo` /
`vite.config.js` artefacts are tracked — see [08](08-risks-limitations-and-improvements.md).

> Next: [04-core-modules-and-business-logic.md](04-core-modules-and-business-logic.md) — what each module owns.
