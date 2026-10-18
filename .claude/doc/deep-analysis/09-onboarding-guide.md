# 09 · Onboarding Guide

> Index: [README.md](README.md) · Previous: [08-risks-limitations-and-improvements.md](08-risks-limitations-and-improvements.md) · Next: [10-glossary.md](10-glossary.md)

## 1. The mental model in five sentences

1. One FastAPI process group owns every rule; everything else (React portal, Android
   app, iOS scaffold) is a thin client of `/api`.
2. MySQL is the only state, migrated exclusively by Alembic; files live in it as blobs.
3. Identity is a short-lived JWT whose claims (`role`, `allowed_classes`,
   `allowed_menus`) are the whole authorisation model; `deps.py` is where it is enforced.
4. Writes follow one order — validate, mutate, commit, publish, notify, log — and the
   browser refreshes itself from the publish step over Server-Sent Events.
5. The same source deploys to a sub-path on a shared host (TEST) and to a dedicated
   domain (PROD) through a handful of build-time knobs.

If you keep those five in mind, every file in the repo has an obvious place.

## 2. Prerequisites

Python 3.12, Node 20+, a MySQL 8 instance you can create a schema in, git, and —
only if you will touch PDFs — WeasyPrint's system libraries (`brew install pango cairo
gdk-pixbuf libffi` on macOS). Android Studio for the app; Xcode + `xcodegen` for iOS.
Read `.claude/skills/kis-design-system/SKILL.md` before any UI or print change.

## 3. Reading order (files, not docs)

| Day | Read | Why |
|---|---|---|
| 1 | `.claude/CLAUDE.md` (top, Gotchas, Next Steps); `backend/app/main.py`, `deps.py`, `security.py`, `constants.py`, `permissions.py`; `frontend/src/App.tsx`, `lib/api.ts`, `lib/auth.ts`, `components/ProtectedRoute.tsx` | who can do what, and how the two halves are wired |
| 2 | `backend/app/models/` (all), `alembic/versions/0001_initial.py` and `0013_component_term.py`; `routers/students.py`, `schemas/student.py`, `routers/_bulk.py`; `frontend/src/pages/Students.tsx`, `types/api.ts` | the richest entity end to end, including the approval queue and bulk import |
| 3 | `routers/marks_batches.py`, `routers/marks.py`, `services/results.py`, `models/class_subject.py`, `seed/exam_pattern.py`; `pages/MarksEntry.tsx`, `pages/MarksResults.tsx`; `routers/attendance.py`, `pages/Attendance.tsx` | the academic core: components, batches, scopes, grades |
| 4 | `backend/app/pdf/` (all), `routers/pdf_templates.py`, `pages/TemplateDetail.tsx`; `events.py`, `routers/stream.py`, `lib/sse.ts`, `lib/version.ts` | print pipeline, cache, realtime, cache busting |
| 5 | `scripts/deploy/common/lib.sh`, `scripts/deploy/test/env.sh`, `deploy/nginx.school.conf`, `deploy/nginx.kisschool.conf`, `deploy/school-management.service`, `scripts/provision/provision.sh`; `android/.../di/AppContainer.kt`, `data/api/ApiService.kt`, `ui/nav/AppNav.kt`, `ui/update/UpdateGate.kt` | how it ships, and the mobile client |

The `.claude/GOTCHAS_*.md` archives and `.claude/memory/` are worth a skim whenever a
design looks strange — the reason is almost always written down.

## 4. Local setup, step by step

```bash
git clone <repo> && cd school-management
git config core.hooksPath .githooks          # arms the commit-message guard (per clone)

# --- backend ---
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mysql -u root -p -e "CREATE DATABASE school_management CHARACTER SET utf8mb4;
  CREATE USER 'school'@'localhost' IDENTIFIED BY 'devpass';
  GRANT ALL ON school_management.* TO 'school'@'localhost';"
cat > .env <<'ENV'
DATABASE_URL=mysql+pymysql://school:devpass@localhost:3306/school_management
JWT_SECRET=dev-only-secret
JWT_EXPIRY_HOURS=8
LOG_JSON=0
ENV
alembic upgrade head                          # creates all 20 tables
uvicorn app.main:app --reload --port 8000     # run FROM backend/ so .env is found
# first boot seeds admin_auth / super_admin_auth with the defaults from config.py

# --- frontend (second terminal) ---
cd ../frontend && npm ci && npm run dev
# open http://localhost:5173/school/admin/   (the /school/admin/ base applies in dev too)

# --- public site (optional) ---
cd ../public-site && npm ci && npm run dev:css   # terminal A
npm run dev:html                                  # terminal B → http://localhost:8080/school/
```

Log in with the admin identifier defined as `ADMIN_EMAIL` at the top of
`backend/app/routers/auth.py` and the default password from `config.py`. Create a staff
account from the Staff page to see the class-scoped experience; the 6-digit initial
password is shown once in the response.

To get realistic academic data: as super-admin, open Class Subjects and press
"Seed KIS default pattern" (calls `POST /api/class-subjects/seed-defaults`).

## 5. Your first safe change — a worked recipe

Goal: add an optional free-text `remarks` field to notices. It touches every layer
without touching anything risky.

| Step | File | What to do |
|---|---|---|
| 1 | `backend/app/models/notice.py` | add `remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)` |
| 2 | `backend/alembic/versions/0014_notice_remarks.py` | copy the header style of `0013_component_term.py`; `revision="0014_notice_remarks"`, `down_revision="0013_component_term"`; `op.add_column("notices", sa.Column("remarks", sa.String(500), nullable=True))` and the matching `drop_column`. Keep it additive. |
| 3 | `backend/app/schemas/notice.py` | add `remarks: str | None = None` to the create and out models |
| 4 | `backend/app/routers/notices.py` | pass `remarks=payload.remarks` when constructing `Notice` |
| 5 | `frontend/src/types/api.ts` | add `remarks: string | null` to `Notice` |
| 6 | `frontend/src/pages/Notices.tsx` | add a `Textarea` to the form and a cell to the table |
| 7 | `packages/design-system/i18n/portal-en.json` and `portal-pa.json` | add `portal.notices.remarks` in **both** files |
| 8 | Android (only if the app shows notices — today it does not) | nothing |

Verify locally: `alembic upgrade head`, create a notice with remarks, see it appear
live in a second tab (that is the SSE path working), `cd frontend && npx tsc -b`.
Commit with a conventional message (`feat(notices): optional remarks`), no AI trailer.

A frontend-only first change: translate one English table header on
`frontend/src/pages/Fees.tsx` with `<T k="portal.fees.someKey" />` plus the two JSON keys.

## 6. Checklist before you deploy

- [ ] `python3 -c "import ast,pathlib;[ast.parse(p.read_text()) for p in pathlib.Path('backend').rglob('*.py')]"` passes (the deploy script does this too)
- [ ] `cd frontend && npx tsc -b` passes (do **not** use `--noEmit`, it fails on this project's references)
- [ ] every response-shape change is mirrored in `frontend/src/types/api.ts` and, if the app uses it, in `android/.../data/api/dto/`
- [ ] every new string has `en` and `pa`
- [ ] every new endpoint takes a `deps.py` dependency and, if it has a class, calls `assert_class_allowed`
- [ ] every new list query filters `status != deleted` where the table has soft delete
- [ ] new `log.*(extra=…)` keys avoid Python's reserved `LogRecord` names
- [ ] a new table or column has an Alembic revision, and a new model is imported in `backend/alembic/env.py`
- [ ] if you learned something non-obvious, add a Gotcha to `.claude/CLAUDE.md` (or run `/save-session`) and update the affected document in this folder

## 7. Deploying

| You changed | Command | Notes |
|---|---|---|
| frontend only | `/deploy-test-frontend` | rebuilds and rsyncs `dist/`; run `scripts/build-android.sh test` first if the APK must survive (`rsync --delete`) |
| backend only, no migration | `/deploy-test` | snapshot → rsync → pip → `alembic upgrade head` → restart → health |
| anything with a migration, or both halves | `/deploy-test-all` | the everyday "ship it" |
| public site | `/deploy-test-public-site` | Eleventy build + rsync |
| Android APK | `/release-android` (asks `prod` or `test`, then `y/N`) | bumps version, builds, verifies the APK is downloadable, then publishes the force-update manifest |
| to production | the `/deploy-prod*` twins | require typing `DEPLOY PROD`; deploy to TEST first and click through |

The scripts snapshot `app/` and the database before touching anything and roll back the
code automatically if the health check fails. Manual rollback:
`bash scripts/deploy/test/rollback.sh` lists snapshots, `… rollback.sh <timestamp>`
restores one (production has no wrapper yet — see 08 B5).

## 8. Debugging a production issue

1. **Get the request id.** In the browser's Network tab the failing response carries
   `X-Request-ID`; the Android app does not surface it (log the time instead).
2. **Look at the logs.** `/check-logs 30m` (or `bash scripts/deploy/prod/check-logs.sh 30m`)
   streams service status, `journalctl`, the error log tail, recent tracebacks, the access
   tail and recent 4xx/5xx. For a specific id: `grep <request_id> /opt/school-management/logs/app.error.log`
   on the server — every JSON line carries `request_id`, `user_sub`, `user_role`.
3. **Match the signature.**

| Symptom | Likely cause | Where to look |
|---|---|---|
| 401 everywhere after about an hour | token expired (`JWT_EXPIRY_HOURS`, default 1) | `.env`; [06](06-configuration-and-environment.md) |
| 403 `Class not in scope` for a teacher who should have access | `staff_classes` rows (or the "All" sentinel not expanded on an old build) | `constants.py`, `deps.assert_class_allowed` |
| 403 `Admin only` / `Super-admin only` | wrong role for the endpoint | permission matrix in [04](04-core-modules-and-business-logic.md) |
| 409 with a student's name | admission-id or roll-number collision | `routers/students.py::_check_uniqueness` |
| 409 `Batch is submitted (locked)` | teacher saving a locked batch; needs an edit request | `routers/marks_batches.py` |
| 409 `An edit request is already pending` | second edit to the same student | `routers/students.py::update_student` |
| 410 on `/pdf/report-card` | old client calling the retired ad-hoc endpoint | `routers/pdf.py` |
| 422 from the Android app only in release builds | R8 renamed DTO fields | `android/app/proguard-rules.pro` (Gotcha 16) |
| 500 right after a successful save, `KeyError … LogRecord` | reserved logging key | Gotcha 12 |
| 500 `Data truncated for column` | enum without `values_callable` | Gotcha 8 |
| 503 on PDF routes | WeasyPrint libraries missing on the server | `pdf/render.py` docstring |
| Stale UI after deploy | nginx `no-cache` locations missing or not reloaded | Gotcha 15 |
| Some users not auto-refreshing | SSE connected to the other gunicorn worker | 08 B1 |
| Service down right after provisioning | `.env` missing | `scripts/provision/04-write-env.sh` |

4. **Check schema state** if a deploy touched migrations: on the server
   `cd /opt/school-management/app && .venv/bin/alembic current` should print the head
   revision (`0013_component_term` once Session 18 is deployed).
5. **Verify the plumbing** when realtime or caching misbehaves:
   `curl -N "https://<host>/<prefix>api/stream/students?token=<jwt>"` should hold open
   and print pings; `curl -I https://<host>/<prefix>admin/version.json` should show
   `Cache-Control: no-cache, must-revalidate`.
6. **Roll back** if the cause is the new code and a fix will take time (section 7).

## 9. Common mistakes to avoid

* Hardcoding `/school/` or `/admin/` anywhere in the SPA — derive from `import.meta.env.BASE_URL`.
* Running `vite build` directly — always `npm run build` (the committed `vite.config.js` may be stale).
* Treating `user.allowed_classes ?? CLASSES` as safe — an admin's list is `[]`, which is truthy; use `length ? … : CLASSES`.
* Reintroducing `<input type="date">` or a raw bounded `<input type="number">`.
* Adding a class name in one place — there are three lists (Python, TypeScript, Kotlin).
* Forgetting `assert_class_allowed` in a handler that accepts a class.
* Forgetting the soft-delete filter in a new list query.
* Passing `name`, `module`, `filename`, … as `extra=` keys to the logger.
* Defining a MySQL enum model without `values_callable` for hyphenated values.
* Calling `metadata.create_all()` — always Alembic.
* Caching a derived artefact without hashing every input it reads (the report-card lesson, Gotcha 20).
* Expecting `GET /students` to return an array — it returns `{items, total, page, page_size}`.
* Deploying a frontend without rebuilding the APK and wondering where the download went.
* Changing the Android package without updating the ProGuard keep rule.
* Committing anything from `android/keystore/` — and see 08 A1 about the zip that already was.

## 10. Where knowledge lives, and where to put yours

* `.claude/CLAUDE.md` — the live runbook. Add a numbered Gotcha when you are bitten;
  `/save-session` keeps it tidy.
* This folder — the durable explanation. If your change invalidates a sentence here,
  fix the sentence in the same commit, or re-run `/deep-analysis`.
* `.claude/memory/` — the assistant's cross-session notes; you may read them, the
  assistant maintains them.
* Commit messages — conventional, specific, no attribution trailers.

> Next: [10-glossary.md](10-glossary.md) — every term, defined, with a pointer into the code.
