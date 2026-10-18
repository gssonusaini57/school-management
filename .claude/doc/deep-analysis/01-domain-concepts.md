# 01 · Domain Concepts

> Index: [README.md](README.md) · Previous: [00-project-overview.md](00-project-overview.md) · Next: [02-high-level-architecture.md](02-high-level-architecture.md)

This is an Indian K-12 school. Many columns, defaults and validation rules only make
sense if you know how such a school is organised and which documents the state board
expects. Each concept below ends with a pointer to where it lives in the code.

## 1. The school and its board

* **KIS** = Khalsa International Senior Secondary School, Jalalabad, District Patiala,
  Punjab. Established 2005. The brand strings (name, motto "Vidya · Vichar · Seva",
  affiliation number) live in `packages/design-system/i18n/en.json` and `pa.json`.
* **PSEB** = Punjab School Education Board, the state examination board. It matters
  twice: (1) the school is "affiliated" (Aff. No. shown on stationery), and (2) PSEB
  runs the external board exams for classes 10 and 12, for which the school prints
  **admit cards** in a PSEB-mandated layout and date format.
  Code: `backend/app/pdf/templates/pseb-admit-card.html.j2`, `backend/app/pdf/schemas.py`
  (`PsebAdmitCard`), `backend/app/pdf/format.py::format_date_pseb`.
* **Bilingual** operation. Punjab is Punjabi-speaking; official communication is
  English + Punjabi in the **Gurmukhi** script. Every user-facing string has an `en` and
  a `pa` form, and print documents often show both side by side (`Bilingual{en, pa}`
  in `backend/app/pdf/schemas.py`). The portal switches language at runtime
  (`frontend/src/lib/i18n.ts`); the public site is built twice, once per locale
  (`public-site/src/en/`, `public-site/src/pa/`).

## 2. Academic structure

### Classes
Fifteen classes, in this order: Nursery, L.K.G, U.K.G, 1st … 12th. The spelling is
canonical — `"L.K.G"` with dots, not `"LKG"` — because it is a **string key** in
`students.class_name`, `staff_classes.class_name`, `attendance.class_name`,
`marks.class_name`, `class_subjects.class_name` and `pdf_templates.class_name`.
There is no `classes` table. The list is hand-mirrored in three places that must stay
identical: `backend/app/constants.py::CLASSES`, `frontend/src/lib/utils.ts::CLASSES`,
and `android/app/src/main/java/in/kisschool/ui/screens/studentedit/StudentForm.kt`.
`backend/scripts/fix_staff_credentials.py` exists partly to repair legacy misspellings.

### Sessions
An academic year, written `"2025-26"`. It is a free-text `String(20)` everywhere
(`marks.session`, `marks_batches.session`, `pdf_templates.session`). The frontend
proposes the current one with `defaultSession()` in `frontend/src/pages/MarksEntry.tsx`
and `MarksResults.tsx` (calendar year → `"YYYY-YY"`). Nothing validates the format.

### Terms and the "scope" of a result
The year has two terms. A result can be computed for **Term 1**, **Term 2** or the
whole year (**Annual**). The term is not a property of a mark; it is a property of
the *exam component* the mark was entered against (`subject_exam_components.term`:
`1`, `2`, or `NULL` meaning "counts in both terms"). The scope selector is the
`Scope` literal in `backend/app/services/results.py` and the `scope` query parameter
of `GET /api/marks/results`. A report-card template's free-text `term` ("Term I",
"Term II", anything else) is mapped onto a scope by `scope_from_term` in the same file.

### Subjects and categories
Each class has its own subject list (`class_subjects`, unique on
`(class_name, subject_name)`), with an optional Punjabi name and a `category`:

| `category` | Meaning | Effect |
|---|---|---|
| `academic` | marked out of numbers, counts toward totals | appears in the scholastic table of the report card |
| `co_curricular` | Drawing, Rhymes, Conversation/GK, etc. for the youngest classes | also numeric, counts toward totals (the seed gives them marks) |
| `grading` | Computer, Phy. Edu, Agriculture, EVS in higher classes | letter-graded only; MarksEntry hides them (`eligibleSubjects` filter), report card renders them from per-student "co-scholastic" grades instead of marks |

Code: `backend/app/models/class_subject.py`, seed in `backend/app/seed/exam_pattern.py`
(127 subjects, 654 components, derived from a handwritten school sheet; the module
docstring says values need spot-checking).

### Exam components
A subject is assessed through several components, each with its own maximum, e.g.
for classes 1st–5th: `P.T. First` (35), `P.T. Second` (35), `Semester First` (80) in
Term 1 and `P.T. Third`, `P.T. Fourth`, `Semester Second` in Term 2. "P.T." is a
periodic test; "Semester" is the term-end exam; "Oral" exists for the youngest
classes; Maths/Science in some classes split into "Written" and "Practical"
components. A **mark is always entered per component**: the component's name is
stored in `marks.exam_type` and its max in `marks.max_marks`. Code:
`backend/app/models/class_subject.py::SubjectExamComponent`, migration
`backend/alembic/versions/0013_component_term.py` (backfills `term` from the names).

### Marks, batches and locking
A **batch** is the unit a teacher fills in: one `(class, subject, exam_type, session)`
quadruple, with one `marks` row per student. It starts as `draft`, becomes
`submitted` (locked) when the teacher submits, and can only be unlocked by a
super-admin approving a **marks edit request** (which carries a mandatory reason).
Code: `backend/app/models/marks_batch.py`, `backend/app/routers/marks_batches.py`.
Legacy marks (from before Session 13, or from the CSV bulk import) have `batch_id IS NULL`
and are outside this workflow.

### Results, percentages and grades
A result rolls component marks up: per subject, sum the in-scope components the
student has marks for (`obtained`) against the sum of their maxima (`max`); then sum
graded subjects into a grand total. Percentage is `obtained / max`; subjects with
`max == 0` (grading-only) are excluded from totals. The **grade band** is:

| % | Grade |
|---|---|
| ≥ 91 | A1 |
| 81–90 | A2 |
| 71–80 | B1 |
| 61–70 | B2 |
| 51–60 | C1 |
| 41–50 | C2 |
| < 41 | D |

Single source: `grade_for` in `backend/app/services/results.py` (the report-card
template repeats the table as static text on line 168 of
`backend/app/pdf/templates/report-card.html.j2`). A subject's `status` is `complete`,
`partial` or `missing` depending on how many in-scope components have marks — the UI
hides students who are `missing` everywhere. Promotion default on the report card:
`"Promoted"` if ≥ 33 %, else `"Needs improvement"` (`backend/app/pdf/builder.py`).

**Worked example.** A 3rd-class student with Maths `P.T. First` 30/35,
`P.T. Second` 28/35, `Semester First` 70/80 and nothing yet in Term 2: Term 1 scope →
obtained 128, max 150, 85.33 %, grade A2, status `complete`. Annual scope → the same
128 obtained but max 300 (Term 2 components count in the denominator), 42.67 %, grade
C2, status `partial`. The annual figure is "unfair" until Term 2 is entered — this is
why the results page has the scope selector.

## 3. People

### Students
`students` holds the admission form: names (student, father, mother), DOB, gender,
village, phone, Aadhaar, alternate phone, religion, previous school, bank details
(for government scholarship transfers), `annual_fee`, and `class_name`. Three
identifiers coexist:

| Field | Meaning | Rule |
|---|---|---|
| `id` | database primary key | used in every API URL |
| `admission_no` + `admission_id` | the school's ledger number; `admission_id` is derived as `KIS/{year}/{admission_no:04d}` | `admission_id` unique; computed in `routers/students.py::_compute_admission_id` using the record's creation year |
| `roll_no` | the class roll number, a string | unique per `(class_name, roll_no)`; sorted numerically in the UI |

Students carry three **documents** (`student_documents.kind` ∈ `photo`, `dob_cert`,
`aadhar`) stored as blobs in MySQL. Aadhaar is India's 12-digit national ID; phones
are 10 digits — both enforced on bulk import in `routers/students.py` and in the
admissions form.

### Staff
`staff` are teachers and other employees: `employee_id` auto-assigned as
`KIS/EMP/{year}/{seq:04d}` (`routers/staff.py::_next_employee_id`), `designation`,
unique `email`, `phone`, and two authorisation inputs:

* **Assigned classes** (`staff_classes`). A teacher assigned to every class is stored
  as **one row with the literal string `"All"`** — the "All sentinel". It is expanded to
  the full class list at login and on every token decode (`backend/app/constants.py`).
* **Allowed menus** (`staff.allowed_menus`, JSON list of keys such as `"attendance"`,
  `"marks-entry"`, `"students.bulk"`). The registry is `backend/app/permissions.py`,
  mirrored in `frontend/src/lib/menus.ts`.

Staff have two valid passwords at once: their own (`password_hash`, with a
`force_password_change` flag on first issue) and an optional admin-set **temporary
password** (`temp_password_hash`) that lets an admin act for an absent teacher.

### Roles
See the table in [00-project-overview.md](00-project-overview.md). The two admin
roles are not rows in `staff`; they are singleton password rows (`admin_auth`,
`super_admin_auth`) matched by hardcoded email constants in `routers/auth.py`.

## 4. Daily operations

### Attendance
One `attendance` row per `(class_name, date)`, with child `attendance_records` rows
per student. Statuses: `P` present, `A` absent, `L` leave, `H` half day. A day can also
be flagged `is_holiday`, in which case there are no student rows. Saving **replaces**
the whole day's records; `DELETE /attendance` un-marks a day entirely. The Android app
shows a per-class month calendar of marked / missed / holiday days fed by
`GET /attendance/marked-dates`. Code: `backend/app/routers/attendance.py`,
`backend/app/models/attendance.py`.

### Fees
`fee_payments`: one row per payment with `month`, `year`, `amount`, `date` and a
unique `receipt_no` (auto `RC<unix-ms>` if not supplied). Student name and class are
denormalised onto the row so receipts survive later edits. Only admins write fees.
The ad-hoc **fee receipt PDF** is a separate payload (`FeeReceipt` schema) and is not
linked to a `fee_payments` row. Code: `backend/app/routers/fees.py`.

### Notices
`notices` with `priority` (`normal`/`medium`/`high`) and a free-text `audience`. Any
authenticated user can post; only admins delete. Code: `backend/app/routers/notices.py`.

## 5. Governance: soft delete and approval queues

Three queues share one shape — *request with reason → super-admin approves or rejects
with reason* — and one audit style (actor **display names**, not IDs, in
`requested_by`, `reviewed_by`, `added_by`, `updated_by`, `saved_by`).

| Queue | What is requested | Where the state lives | Who approves |
|---|---|---|---|
| Deletion | archive a student or staff member | `status` column: `active` → `pending_delete` → `deleted` (then optional hard purge) | super-admin (`routers/deletion_requests.py`); restore is admin or super-admin |
| Student edit | a field diff `{field: {old, new}}` | `student_edit_requests` | super-admin (`routers/edit_requests.py`); super-admin's own edits apply immediately |
| Marks edit | unlock a submitted batch | `marks_edit_requests` | super-admin (`routers/marks_batches.py`) |

`RecordStatus` is defined once in `backend/app/models/record_status.py`. Deleted rows
are hidden from every normal listing except for super-admins who pass
`include_deleted=true`.

## 6. Stationery and print documents

Six document kinds share a brand frame (`backend/app/pdf/templates/_base.html.j2`):

| Kind | Flow | Payload source |
|---|---|---|
| `letterhead-a`, `letterhead-b` | ad-hoc: form → `POST /api/pdf/{kind}` → download | typed by the admin (`frontend/src/pages/Letterheads.tsx`) |
| `fee-receipt` | ad-hoc | typed; validated against `FeeReceipt` (total must equal item sum) |
| `salary-slip` | ad-hoc | typed (`frontend/src/pages/SalarySlips.tsx`) |
| `report-card` | **templated**: per-class template + per-student data + marks → cached PDF | `pdf_templates`, `pdf_student_data`, `marks` |
| `pseb-admit-card` | templated | `pdf_templates` (centre, school code, date sheet) + `pdf_student_data` (roll no, PSEB registration no) |

A **template** is scoped to `(kind, class, session, term)`; **per-student data** is
everything that varies per student but is not a mark (rank, attendance %, remarks,
co-scholastic grades, PSEB reg no). Format rules from the brand handoff: currency as
`₹ 1,00,000.00` (Indian lakh/crore grouping), dates as `08 May 2026` except PSEB
documents which use `08-05-2026`. Code: `backend/app/pdf/format.py`,
`frontend/src/lib/format.ts`.

## 7. Realtime vocabulary

A **channel** is a named topic a browser subscribes to over Server-Sent Events;
mutating endpoints **publish** `upsert`/`delete`/`bulk` events to it; the frontend
responds by **invalidating** cached queries so they refetch. Channel names:
`students`, `fees`, `notices`, `staff`, `dashboard`, `deletion_requests`,
`edit_requests`, `class_subjects`, `marks_batches`, `marks_edit_requests`
(`backend/app/routers/stream.py`; URL paths use hyphens, broker names use underscores).

## 8. Data-entry conventions you will see enforced

* Names are Title-Cased on import (`routers/_bulk.py::title_case`, `lib/utils.ts::toTitleCase`).
* CSV dates accept `YYYY-MM-DD` (preferred) and the Indian spreadsheet defaults
  `DD-MM-YYYY` / `DD/MM/YYYY` (`_bulk.py::parse_date_field`).
* Religion is a fixed dropdown (`lib/utils.ts::RELIGIONS`); gender defaults to `"Male"`
  on import; several optional text fields default to the literal `"N/A"` rather than NULL.
* Bounded numbers (marks) use the `NumberField` component which rejects out-of-range
  keystrokes; native `<input type="date">` is banned in favour of `DatePicker`
  (see `.claude/CLAUDE.md` gotchas 3 and 13).

> Next: [02-high-level-architecture.md](02-high-level-architecture.md) — how these concepts are arranged into a system.
