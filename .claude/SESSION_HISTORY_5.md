# Session 5 — 2026-05-07 (evening) · UX hardening + bulk import

**Focus:** Fix routing/validation bugs from real user testing; ship CSV bulk import on 4 pages.

**Routing fixes:**
- Discovered sidebar `<NavLink to="/admissions">` produced `/admissions` (matched uploadmytds's nginx catch-all) instead of `/school/admissions`. Added `<BrowserRouter basename={...}>` reading `import.meta.env.BASE_URL` so React Router knows it's mounted under `/school`. Updated `api.ts` 401-redirect to derive `/school/login` from BASE_URL too. Hard-refresh on any deep URL now lands on the right SPA page (nginx `try_files` falls back to `/school/index.html`, React Router takes over).
- Found admin class dropdown was empty: admin JWT has `allowed_classes: []` (full-access marker), and `user?.allowed_classes ?? CLASSES` kept the empty list. Switched all class-dropdown sites to `?.length ? : CLASSES`.

**Form validation (Admissions + Student edit):**
- Phone / Alt phone: `digitsOnly` filter on input, max 10, must be exactly 10 at submit.
- Aadhaar: digits-only, max 12, must be 12 if provided.
- Names (student / father / mother): auto-Title-Case on blur (handles spaces, hyphens, apostrophes — `O'Brien`, `Ram-Kumar`).
- Religion: dropdown (Hindu / Muslim / Sikh / Christian / Jain / Buddhist / Parsi / Other) instead of free text.
- DOB: bounded `min`/`max` via `dobBounds()` (today − 25 years to today) + `onFocus={() => showPicker()}` to auto-open the calendar (avoids Safari's mm/dd/yyyy subfield Tab trap).
- Annual fee: state defaults to `""` not `0` so typing "500" doesn't become "0500"; on Edit, displays `""` when existing value is 0.
- Inline error messages with red-bordered fields, errors clear as soon as the field is edited.
- Helpers added to [frontend/src/lib/utils.ts](../frontend/src/lib/utils.ts): `RELIGIONS`, `toTitleCase`, `digitsOnly`, `dobBounds`. shadcn `SelectTrigger` got an explicit `tabIndex={0}` + 2px focus ring.

**Bulk CSV import (4 entities):**
- Backend: shared [backend/app/routers/_bulk.py](../backend/app/routers/_bulk.py) (read_csv, title_case, parse_date_field, must_str, opt_str). New endpoints `POST /api/{students,attendance,staff,marks}/bulk-import` accept multipart CSV, validate per-row, return `{inserted, errors:[{row, reason, data}]}`. Valid rows commit even when others fail.
- Frontend: shared [BulkImportDialog](../frontend/src/components/BulkImportDialog.tsx) handles template download, file picker, upload, result rendering. Templates live in [frontend/src/lib/templates.ts](../frontend/src/lib/templates.ts) — STUDENTS, ATTENDANCE, STAFF, MARKS each shipped with header + 2-3 sample rows.
- "Bulk import" button added to Students, Attendance, Staff, and MarksEntry pages.
- Iterated on the dialog after user feedback: top-level red banner for HTTP/network errors (so they don't disappear like toasts); sticky-header table of row-level errors with auto-extracted "offending value" column; "Download error report" CSV; Upload button morphs to "Try again" after errors.

**Verified live:**
- All 4 endpoints respond correctly (empty CSV → 0 inserted; valid+invalid mix → only valid rows persisted, errors enumerated with row numbers + reasons).
- Bundle size: 635 KB JS / 206 KB gz (small bump from validation helpers + dialog).
