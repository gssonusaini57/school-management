# 00 · Project Overview

> Index: [README.md](README.md) · Next: [01-domain-concepts.md](01-domain-concepts.md)

## In one paragraph

The KIS School Management Portal is the internal administration system of a single
school: **Khalsa International Senior Secondary School**, Jalalabad, District
Patiala, Punjab, affiliated to the Punjab School Education Board (PSEB). Administrators
and teachers use it every working day to admit students, keep student records and
documents, mark attendance, enter and publish exam marks, record fee payments, post
notices, manage staff accounts, and print branded stationery (letterheads, fee
receipts, salary slips, report cards, PSEB admit cards). It is a FastAPI + MySQL
backend, a React single-page admin portal, a static bilingual marketing site, a
native Android app for teachers, and an iOS scaffold, all living in this one repository.

## The problem it solves, and where it came from

The first version (May 2026, see `.claude/SESSION_HISTORY_1_2.md`) was a single
2,300-line `index.html` talking directly to Firebase Firestore from the browser,
hosted on GitHub Pages. The archived file is kept at `_archive/index.firebase.html`
for reference only. That design had four problems that drove the rewrite:

1. **No real security.** Firestore and Storage rules were effectively open, and the
   admin password was stored in plaintext in a document.
2. **Operational pain.** Every rules change had to be deployed by hand in the Firebase
   console; GitHub Pages CDN caching made every release look broken until a hard refresh.
3. **Vendor coupling.** Eight `onSnapshot` listeners tied the UI to Firestore APIs.
4. **No server.** Nothing could be validated, audited, rate-limited or rendered (PDFs) server-side.

Session 3 replaced it with an owned backend (`backend/`), a typed frontend
(`frontend/`) and a repeatable deploy framework (`scripts/`, `deploy/`). Everything
since then builds on that foundation. Read `.claude/SESSION_HISTORY_3.md` for the
migration itself and [02-high-level-architecture.md](02-high-level-architecture.md)
for how it evolved afterwards.

## Who uses it

Three roles exist. They are not stored in a users table; they are a JWT claim issued
by `backend/app/routers/auth.py` and enforced by `backend/app/deps.py`.

| Role | Who, in the school | How they log in | What they can do |
|---|---|---|---|
| `super_admin` | one person (singleton row in `super_admin_auth`) | a hardcoded email constant in `routers/auth.py` + password | everything, plus the approval queues: deletion requests, student edit requests, marks edit requests, and the class-subjects master |
| `admin` | one person (singleton row in `admin_auth`) | a second hardcoded email constant + password | all day-to-day administration; edits and deletions they make to students are **queued for super-admin approval** rather than applied |
| `staff` | teachers (`staff` table) | their own email **or** phone + password; an admin-set temporary password also works | only the classes in `staff_classes` and only the menus in `staff.allowed_menus`; can request edits/deletions but not approve |

**UNKNOWN / needs owner confirmation:** the number of staff and students in
production, and which real people hold the two singleton roles. `.claude/CLAUDE.md`
lists admin login emails that differ from the constants currently in
`backend/app/routers/auth.py`; treat the code as authoritative and confirm with the owner.

## What it does

| Capability | Portal route (`frontend/src/pages/`) | API (prefix `/api`) | Main tables |
|---|---|---|---|
| Dashboard KPIs + per-class chart | `/dashboard` (`Dashboard.tsx`) | `/students`, `/staff`, `/fees`, `/notices`, `/attendance/today-summary` | several |
| Admissions + student records + documents | `/admissions`, `/students`, `/students/:id` | `/students`, `/students/{id}/documents/{kind}`, `/files/students/...` | `students`, `student_documents` |
| Student edit approval | `/edit-requests` (super-admin) | `/admin/edit-requests` | `student_edit_requests` |
| Soft delete + approval | `/deletion-requests` (super-admin) | `/admin/deletion-requests` | `students.status`, `staff.status` |
| Attendance (P/A/L/half-day/holiday) | `/attendance` | `/attendance`, `/attendance/marked-dates` | `attendance`, `attendance_records` |
| Class subjects + exam components master | `/class-subjects`, `/class-subjects/:id` (super-admin) | `/class-subjects` | `class_subjects`, `subject_exam_components` |
| Marks entry with draft → submit → lock | `/marks/entry` | `/marks/batches`, `/admin/marks-edit-requests` | `marks`, `marks_batches`, `marks_edit_requests` |
| Term-scoped results table | `/marks/results` | `/marks/results` | `marks` + master tables |
| Fees | `/fees` | `/fees` | `fee_payments` |
| Notices | `/notices` | `/notices` | `notices` |
| Staff accounts, menus, temp passwords | `/staff` (admin) | `/staff` | `staff`, `staff_classes` |
| Reports | `/reports` (admin) | `/reports/*` | read-only aggregates |
| Ad-hoc PDFs (letterheads, salary slips) | `/letterheads`, `/salary-slips` | `POST /pdf/{kind}` | none (rendered on the fly) |
| Templated bulk PDFs (report cards, PSEB admit cards) | `/templates`, `/templates/:id` | `/pdf/templates/...`, `/pdf/cache/{id}` | `pdf_templates`, `pdf_student_data`, `pdf_cache` |
| Password reset by email | `/forgot-password`, `/reset-password` | `/auth/forgot-password`, `/auth/reset-password` | `password_reset_tokens` |
| Realtime refresh | every list page | `GET /stream/{channel}?token=` (SSE) | in-memory |
| Teacher mobile app | `android/` | same API | same |

## Surfaces and live environments

| Surface | TEST | PROD |
|---|---|---|
| Public marketing site (`public-site/`) | `https://expressonly.in/school/` | `https://kisschool.in/` |
| Staff portal SPA (`frontend/`) | `https://expressonly.in/school/admin/` | `https://kisschool.in/admin/` |
| API (`backend/`) | `https://expressonly.in/school/api/` | `https://kisschool.in/api/` |
| Health | `…/school/api/health` | `…/api/health` |
| Android APK | `…/school/downloads/kis-attendance.apk` (staging flavour) | `…/downloads/kis-attendance.apk` (prod flavour) |
| Server | `104.237.5.113`, shared with the sister project `uploadmytds` and its MySQL | `69.62.72.137`, shared with an unrelated Java/Tomcat application |
| nginx config | snippet `deploy/nginx.school.conf` included in the `expressonly.in` server block | standalone vhost `deploy/nginx.kisschool.conf` |

The same source serves both layouts; the path prefix is a build-time knob
(see [06-configuration-and-environment.md](06-configuration-and-environment.md)).

## Who maintains it

* A single developer (`manjeetsaini85` in git) working with an AI coding assistant in
  numbered "sessions". The session notes under `.claude/` are therefore the project's
  design-decision log and are unusually complete; use them.
* Git history was **squashed** into one root commit on 2026-05-16 (`307b7fc`); there
  are 20 commits since. Day-to-day work lands on `dev`; `master` is the GitHub default
  branch. Several recent `dev` commits were unpushed and undeployed when `.claude/CLAUDE.md`
  was last written (migration `0013` is the important one) — check `git status`
  before assuming parity between repo, test and prod.
* Repository: `github.com/gssonusaini57/school-management`
  (**UNKNOWN / needs owner confirmation:** whether it is public or private; this
  matters a great deal for finding #1 in [08-risks-limitations-and-improvements.md](08-risks-limitations-and-improvements.md)).
* There is **no automated test suite** in the repository. Verification is manual plus
  two cheap gates run by the deploy scripts: an AST parse of all backend Python and a
  TypeScript project build.

## How it fits into a larger ecosystem

```
  uploadmytds (sister project, same owner) ──shares──▶ TEST VPS 104.237.5.113
        │  deploy-framework conventions copied         ├── nginx (expressonly.in)
        ▼                                              ├── MySQL 8 (school_management schema)
  scripts/{provision,deploy}/ · .claude/commands/      └── systemd: school-management (gunicorn :8000)

  Brand agency handoff (_handoff/khalsa-international-handoff/)
        │  tokens · i18n strings · document JSON schemas · brand SVG/PNG
        ▼
  packages/design-system/  ──consumed by──▶  frontend/  public-site/  backend/app/pdf/

  Zoho Mail (info@ mailbox) ◀── backend/app/mailer.py  (password reset, approval notifications)

  Google Fonts CDN ◀── frontend/index.html · public-site/src/_includes/base.njk · backend/app/pdf/templates/_base.html.j2
```

## Where things stand (snapshot, 2026-10-18)

* PROD and TEST both run migrations through `0012`. Branch `dev` carries `0013`
  (term on exam components, wider `marks.exam_type`, marks-aware PDF cache) and the
  "All" class-sentinel fix — committed, **not deployed**.
* Android app `in.kisschool` v1.2.5 build 18 is the current teacher app (prod and
  staging flavours, force-update gate).
* iOS app is a compiling SwiftUI scaffold with none of the features added since
  Session 7; distribution is blocked on an Apple Developer account.
* Bilingual (English + Punjabi) coverage: public site complete; portal chrome and a
  few pages complete; most data pages English-only.

The authoritative "what next" list is the **Next Steps** section of `.claude/CLAUDE.md`.

## Goals and explicit non-goals

**Goals** that explain many decisions: zero-ops hosting on a shared VPS; one source
tree deployable to two path layouts; no third-party data stores beyond MySQL; print
output that matches the school's brand and PSEB formats exactly; usable on cheap
Android phones without the Play Store.

**Non-goals** (as of today): multi-school tenancy; a parent/student app (the brand
handoff specifies one, the repo defers it); high availability; horizontal scaling
(the realtime design assumes a single process, see
[07-design-patterns-and-tradeoffs.md](07-design-patterns-and-tradeoffs.md)).

> Next: [01-domain-concepts.md](01-domain-concepts.md) — the vocabulary you need before the code makes sense.
