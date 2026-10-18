# 10 · Glossary

> Index: [README.md](README.md) · Previous: [09-onboarding-guide.md](09-onboarding-guide.md)

Domain terms, internal jargon and acronyms, alphabetically. "Where" points to the
file that defines or best illustrates the concept.

| Term | Meaning | Where |
|---|---|---|
| **Aadhaar** | India's 12-digit national identity number; stored per student, optionally with a scanned copy as a document | `students.aadhar`; validation in `backend/app/routers/students.py` (bulk import) |
| **Access code** | the *old* staff credential (bcrypt hash + last-4 lookup) from before Session 10; columns dropped by migration `0005_staff_auth` | `backend/alembic/versions/0001_initial.py`, `.claude/GOTCHAS_1_6.md` item 3 |
| **Admin / Super-admin** | the two singleton roles; admin runs the school day to day, super-admin approves edits/deletions and owns the class-subjects master | `backend/app/routers/auth.py`, `backend/app/deps.py`, `models/admin.py` |
| **Admission number / Admission ID** | the school ledger number (`admission_no`) and its derived unique label `KIS/{year}/{no:04d}` (`admission_id`) | `routers/students.py::_compute_admission_id`, migration `0004` |
| **Alembic** | the migration tool; `alembic upgrade head` runs on every backend deploy; revisions `0001`–`0013` | `backend/alembic/` |
| **"All" sentinel** | a single `staff_classes` row with the literal `"All"` meaning every class; expanded to the real list at login and on token decode | `backend/app/constants.py`, Gotcha 21 |
| **Allowed classes** | the JWT claim listing the classes a staff member may touch; empty for admin roles | `security.create_token`, `deps.assert_class_allowed` |
| **Allowed menus / menu key** | per-staff grants (`dashboard`, `students`, `students.bulk`, `attendance`, `marks-entry`, …) deciding which portal menus appear; admins ignore them | `backend/app/permissions.py`, `frontend/src/lib/menus.ts` |
| **Annual / Term 1 / Term 2 (scope)** | the three ways to roll marks up; decided by each exam component's `term` | `backend/app/services/results.py::Scope` |
| **APK, flavour** | the Android package; `prod` flavour (`in.kisschool`, production API) and `staging` flavour (`in.kisschool.test`, TEST API, published under the stable `kis-attendance.apk` name) | `android/app/build.gradle.kts`, `scripts/build-android.sh` |
| **APP_BASE_URL** | the portal URL used to build emailed links (reset, approvals) | `backend/app/config.py` |
| **Approval queue** | request-with-reason → super-admin approve/reject; three instances: deletions, student edits, marks edits | `routers/deletion_requests.py`, `edit_requests.py`, `marks_batches.py` |
| **Attendance status** | `P` present, `A` absent, `L` leave, `H` half day; a day may instead be a **holiday** with no records | `backend/app/models/attendance.py` |
| **Audit columns** | `added_by`, `updated_by`, `saved_by`, `requested_by`, `reviewed_by` — display names of the actor | every model |
| **Base path / BASE_URL** | the URL prefix the SPA is served under (`/school/admin/` on TEST, `/admin/` on PROD); build-time `VITE_BASE`, runtime `import.meta.env.BASE_URL` | `frontend/vite.config.ts`, `frontend/src/main.tsx` |
| **Batch (marks)** | one `(class, subject, exam_type, session)` unit of marks entry with `draft`/`submitted` status | `backend/app/models/marks_batch.py` |
| **Bilingual** | every string in English and Punjabi; `{en, pa}` objects in PDFs, `t()` in the portal, `t(lang)` filter on the public site | `backend/app/pdf/schemas.py::Bilingual`, `frontend/src/components/T.tsx`, `public-site/eleventy.config.cjs` |
| **Broker** | the in-memory publish/subscribe object feeding SSE; one per worker process | `backend/app/events.py` |
| **Build ID / version.json** | a per-build token embedded in the bundle and written next to it; the SPA reloads when they differ | `frontend/vite.config.ts`, `frontend/src/lib/version.ts` |
| **Bulk import** | CSV upload endpoints for students, staff, attendance, marks (legacy) and class subjects; atomic, structured errors | `backend/app/routers/_bulk.py`, `frontend/src/components/BulkImportDialog.tsx`, `lib/templates.ts` |
| **Category (subject)** | `academic`, `co_curricular` (numeric) or `grading` (letter only) | `backend/app/models/class_subject.py::SubjectCategory` |
| **Channel** | an SSE topic (`students`, `fees`, `notices`, `staff`, `dashboard`, `deletion_requests`, `edit_requests`, `class_subjects`, `marks_batches`, `marks_edit_requests`) | `backend/app/routers/stream.py` |
| **Class** | one of 15 canonical names from Nursery to 12th; a string key, not a table | `backend/app/constants.py::CLASSES` (+ two mirrors) |
| **Class scope** | the rule that staff may only read or write their assigned classes | `deps.assert_class_allowed` |
| **Class subjects master** | per-class list of subjects and their exam components, owned by super-admin | `routers/class_subjects.py`, `seed/exam_pattern.py` |
| **Co-scholastic** | non-marked assessments on the report card (grades per "head" such as Discipline), stored as per-student PDF data, not as marks | `backend/app/pdf/schemas.py::ReportCardStudentData` |
| **Component (exam component)** | one assessed part of a subject with its own max marks and term, e.g. `P.T. First` (35), `Semester First` (80) | `models/class_subject.py::SubjectExamComponent` |
| **CurrentUser** | the decoded identity passed to handlers: `sub`, `role`, `name`, `allowed_classes`, `allowed_menus` | `backend/app/deps.py` |
| **Deletion request** | the `pending_delete` state awaiting super-admin approval | `models/record_status.py`, `routers/deletion_requests.py` |
| **Design system / tokens** | the shared palette, fonts, spacing and i18n JSON from the brand handoff | `packages/design-system/`, `.claude/skills/kis-design-system/SKILL.md` |
| **Edit request** | a queued student field diff `{field: {old, new}}` | `models/student_edit_request.py`, `routers/edit_requests.py` |
| **Employee ID** | `KIS/EMP/{year}/{seq:04d}`, auto-assigned per staff member | `routers/staff.py::_next_employee_id` |
| **Exam type** | the column name that, since Session 13, holds a component name | `models/marks.py` |
| **Force-update gate** | the Android overlay that blocks builds below `min_version_code` from `app-version.json`; fails open | `android/.../ui/update/UpdateGate.kt`, `AppUpdateRepository.kt` |
| **Gotcha** | a numbered lesson in `.claude/CLAUDE.md` (older ones in `GOTCHAS_*.md`) | `.claude/` |
| **Grade band** | A1 ≥ 91 … D < 41 | `services/results.py::grade_for` |
| **Gurmukhi** | the script Punjabi is written in; rendered with Noto Sans Gurmukhi via the `lang="pa"` attribute | `frontend/src/components/T.tsx`, `packages/design-system/tokens.css` |
| **Handoff** | the brand agency's design package; read-only source of tokens, strings and document schemas | `_handoff/khalsa-international-handoff/` |
| **Holiday** | `attendance.is_holiday = true` for a `(class, date)` with no student records | `models/attendance.py`, `routers/attendance.py` |
| **Inline URL** | a file or PDF URL carrying the JWT as `?token=` so `<img>` and `<a download>` work | `routers/files.py`, `frontend/src/lib/api.ts::fileUrl`, `lib/pdf.ts::cachedPdfUrl` |
| **JWT** | the HS256 bearer token; expiry `JWT_EXPIRY_HOURS` (default 1) | `backend/app/security.py` |
| **KIS** | Khalsa International Senior Secondary School, Jalalabad, District Patiala, Punjab | `packages/design-system/i18n/en.json` |
| **Letterhead A / B** | the classic centred and the modern letterhead layouts (ad-hoc PDFs) | `backend/app/pdf/templates/letterhead-a.html.j2`, `letterhead-b.html.j2` |
| **LONGBLOB** | MySQL binary column used for student documents and cached PDFs | `models/document.py`, `models/pdf_template.py::PdfCache` |
| **Marks edit request** | a reasoned request to unlock a submitted batch | `models/marks_batch.py::MarksEditRequest` |
| **Nav mode** | topbar (default) or sidebar navigation, persisted per browser | `frontend/src/lib/nav-mode.ts`, `components/Layout.tsx` |
| **Never-raises** | the decorator guaranteeing notification helpers cannot fail the request | `backend/app/notifications.py::_never_raises` |
| **P.T.** | periodic test; the small in-term exam components (`P.T. First` … `P.T. Fourth`) | `backend/app/seed/exam_pattern.py` |
| **PDF cache / source_hash** | stored rendered PDFs keyed by `(kind, student, template, version)` plus a SHA-1 of the marks and student data they were rendered from | `pdf/render_or_cache.py`, migration `0013` |
| **PDF template / per-student data** | class-level print configuration (`pdf_templates`) and per-student non-mark fields (`pdf_student_data`), both scoped by `(kind, session, term)` | `models/pdf_template.py`, `routers/pdf_templates.py` |
| **PROD / TEST** | `kisschool.in` at the domain root vs `expressonly.in/school/` on a shared host | `scripts/deploy/prod/env.sh`, `scripts/deploy/test/env.sh` |
| **PSEB** | Punjab School Education Board; the school's affiliation and the issuer of class 10/12 board exams; mandates the admit-card layout and `DD-MM-YYYY` dates | `backend/app/pdf/templates/pseb-admit-card.html.j2`, `pdf/format.py::format_date_pseb` |
| **RecordStatus / soft delete** | `active` → `pending_delete` → `deleted` on students and staff; hard purge is a separate explicit step | `models/record_status.py` |
| **Report card** | the templated per-student PDF built from marks (via the results engine), template data and per-student data | `backend/app/pdf/builder.py::build_report_card_payload` |
| **Roll number** | class-scoped student number (string), unique per `(class_name, roll_no)` | `models/student.py` |
| **Scope** | see Annual / Term 1 / Term 2 | `services/results.py` |
| **Session (academic)** | the school year as free text, e.g. `2025-26` | `frontend/src/pages/MarksEntry.tsx::defaultSession` |
| **Session (SQLAlchemy)** | the per-request database unit of work from `get_db` | `backend/app/db.py` |
| **Snapshot / rollback** | the pre-deploy `app_<ts>.tgz` + `db_<ts>.sql.gz` and the code-only restore | `scripts/deploy/common/lib.sh` |
| **SSE** | Server-Sent Events, the one-way realtime channel from server to browser | `routers/stream.py`, `frontend/src/lib/sse.ts` |
| **Staging flavour** | the Android build that talks to TEST (`in.kisschool.test`); named `staging` because AGP forbids flavour names starting with `test` | `android/app/build.gradle.kts` |
| **staleTime** | TanStack Query's 30-second freshness window before a mounted query refetches | `frontend/src/main.tsx` |
| **Temp password** | an admin-set second staff credential that does not replace the teacher's own | `models/staff.py::temp_password_hash`, `routers/staff.py` |
| **Term (component)** | `1`, `2` or `NULL` (both) on an exam component; drives scope membership | `models/class_subject.py` |
| **term_key** | `term` with `NULL` mapped to `""` so MySQL unique constraints work | `models/pdf_template.py` |
| **Title case** | `"raj KUMAR"` → `"Raj Kumar"` applied to imported and typed names | `routers/_bulk.py::title_case`, `frontend/src/lib/utils.ts::toTitleCase` |
| **uploadmytds** | the owner's sister project sharing the TEST VPS, its MySQL and the deploy-script conventions | `.claude/memory/project_shared_vps.md` |
| **WeasyPrint** | the HTML/CSS → PDF renderer; needs system libraries and Gurmukhi fonts on the server | `backend/app/pdf/render.py` |
| **X-Request-ID** | response header and log field tying a client error to its log lines | `backend/app/middleware.py` |
| **Zoho** | the mail provider behind the school's transactional mailbox | `backend/app/mailer.py`, `config.py` SMTP settings |
| `/check-logs`, `/deploy-*`, `/release-android`, `/save-session`, `/deep-analysis` | the project's slash commands wrapping `scripts/` | `.claude/commands/` |

> Back to the index: [README.md](README.md)
