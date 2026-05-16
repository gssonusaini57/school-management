---
name: CSV bulk-import pattern (template + dialog + per-row errors)
description: For any list-style page in this project, "Bulk import" should mean a Download Template button + CSV file picker + per-row validation that returns errors with row numbers, reasons, and original data — never abort on the first bad row.
type: feedback
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
When the user asked for bulk import on Students / Attendance / Staff / MarksEntry pages, the requirements were:

1. **Download template** — a CSV with the right column headers + 2-3 example rows so the user can open it in Excel and just fill rows.
2. **Upload** — pick the filled CSV, post to the backend.
3. **Per-row error reporting** — bad rows return a reason ("phone must be 10 digits, got '123'") with the original row data; valid rows in the same file still get inserted. Don't abort on the first error.
4. **Errors stay on screen** — toasts that auto-dismiss in 4s are not enough. The user must be able to read each error, fix the file, and re-upload without closing the dialog.

The pattern that ships in this repo:
- **Backend:** Each `POST /api/<entity>/bulk-import` endpoint imports `read_csv`, `must_str`, `opt_str`, `title_case`, `parse_date_field` from [backend/app/routers/_bulk.py](../../../Documents/GitHub/school-management/backend/app/routers/_bulk.py). Iterates rows, validates, accumulates `errors[]` (each `{row, reason, data}`), commits valid rows in one `db.commit()`. Response is always `{inserted: N, errors: [...]}`.
- **Frontend:** Shared [BulkImportDialog](../../../Documents/GitHub/school-management/frontend/src/components/BulkImportDialog.tsx) takes `templateCsv`, `templateFilename`, `uploadPath`, and an `onSuccess` callback for query invalidation. It renders: how-it-works box, Download template button, file picker (with size display), top-level red error banner for HTTP failures, sticky-header error table (row + reason + auto-extracted offending value), and a "Download error report" CSV with all failed rows + reasons. Upload button morphs to "Try again" when there are errors so the user iterates without closing.
- **Templates:** Static CSV strings in [frontend/src/lib/templates.ts](../../../Documents/GitHub/school-management/frontend/src/lib/templates.ts) (`STUDENTS_TEMPLATE`, `ATTENDANCE_TEMPLATE`, `STAFF_TEMPLATE`, `MARKS_TEMPLATE`).

**How to apply:** When the user asks for bulk import on any future entity (Notices, Fees, etc.), add (a) a new constant in `templates.ts`, (b) a `<BulkImportDialog>` instance on the page with that template + a new `/api/<entity>/bulk-import` endpoint, (c) a backend endpoint following the same `try-per-row, accumulate errors, commit valid rows` shape. Don't fragment the UX with a different dialog or a different response shape.
