---
name: Class-templated bulk PDF flow shipped
description: Session 8 added a per-class template + per-student data + cached-blob flow for Report Cards and PSEB Admit Cards. Routes at /admin/templates; tables pdf_templates, pdf_student_data, pdf_cache.
type: project
originSessionId: 065ecbcc-fa71-4b04-95e0-ab8009b0e8a6
---
**What it is:** A 3-step admin flow that replaces the old single-shot PSEB / Report-Card forms.

1. Admin creates a `PdfTemplate` for a `(kind, class_name, session, term)` scope. `kind` is one of `report-card` or `pseb-admit-card`. The `data` JSON holds class-level fields only (centre, exam time, date sheet, signatures, co-scholastic head labels, etc.) and is validated by `TEMPLATE_SCHEMA_BY_KIND` (in `backend/app/pdf/schemas.py`) on save.

2. Admin fills in per-student fields in a spreadsheet. Stored as `PdfStudentData` rows keyed `(kind, student_id, session, term_key)`. Validated by `STUDENT_DATA_SCHEMA_BY_KIND`. For PSEB: `rollNo, regNo, category, differentlyAbled`. For report-card: `coScholasticGrades (list of {head, grade}), remarks (Bilingual), attendancePct, workingDays, daysPresent, rank, classSize, promotion, house, admissionNo`.

3. Admin selects students and POSTs `/api/pdf/templates/{id}/render`. For each student:
   - Cache lookup on `(kind, student_id, template_id, template_version)`. Hit → return cached `pdf_id`.
   - Miss → builder.py merges (template + Student row + per-student data + Marks rows for report-cards) → validated `ReportCard` / `PsebAdmitCard` model → WeasyPrint → store LONGBLOB in `pdf_cache` → return new `pdf_id`.

Editing a template (PATCH) bumps `version`, which silently invalidates the cache (next request misses and re-renders).

**Where the code lives:**
- Models: `backend/app/models/pdf_template.py` (PdfTemplate, PdfStudentData, PdfCache, TemplateKind enum).
- Migration: `backend/alembic/versions/0002_pdf_templates_cache.py`.
- Schemas: `ReportCardTemplateData / ReportCardStudentData / PsebAdmitCardTemplateData / PsebAdmitCardStudentData` in `backend/app/pdf/schemas.py`.
- Builder: `backend/app/pdf/builder.py` (pure functions; no DB).
- Cache logic: `backend/app/pdf/render_or_cache.py`.
- Router: `backend/app/routers/pdf_templates.py` — exposes two routers (`/pdf/templates` + `/pdf/cache`).
- Frontend: `frontend/src/pages/Templates.tsx` (list + new dialog), `TemplateDetail.tsx` (3 stacked sections).

**Why a separate `pdf_cache` instead of extending `student_documents`?** StudentDocument's enum (`photo|dob_cert|aadhar`) is for identity files; mixing generated artefacts there blurs the model. Same MySQL LONGBLOB pattern, different table, different enum.

**Watch out for:**
- `pdf_templates` router MUST be registered BEFORE the legacy `pdf` router in `main.py` — otherwise `POST /pdf/{kind}` (catch-all) shadows `POST /pdf/templates`.
- The legacy ad-hoc endpoint `POST /api/pdf/{report-card,pseb-admit-card}` returns 410 Gone. The other 4 kinds (letterhead-a/b, fee-receipt, salary-slip) still work for ad-hoc generation.
- `PdfTemplate.term` is nullable; `term_key` is a non-null mirror (`""` when null) so the unique constraint over `(kind, class, session, term_key)` works correctly. Same idea on `pdf_student_data`.
- SQLAlchemy `Enum(TemplateKind, values_callable=…, native_enum=False)` — without `values_callable` it sends the Python attribute name (`pseb_admit_card`) and MySQL ENUM (which has the value `pseb-admit-card`) returns `Data truncated`.

**Verified live:** Render → cache → version bump → re-render cycle confirmed end-to-end on https://expressonly.in/school/admin/templates.
