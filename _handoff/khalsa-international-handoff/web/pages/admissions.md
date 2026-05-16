# Admissions (`/admissions`)


## Sections
1. Hero — `Admissions for 2026–27 are open.`
2. **Process** — 4-step horizontal flow (Pick up form → Submit + interaction → Result → Pay & confirm).
3. **Eligibility** — table by class (age cut-off, prior schooling).
4. **Fees** — `PdfTable`-styled `<table>`. Use `docs.feeReceipt.*` strings. Quarterly + annual columns. Footnote re: late fee.
5. **Documents required** — bilingual checklist.
6. **Apply** — embedded form with: child name, parent name, contact, class, optional message. POST → `/api/admissions/enquiry`.
7. **Walk-in** — hours and address; map.

## Components: `Card`, `Input`, `Select`, `Button`, `Checkbox` (consent), `Badge` (status).

## Form validation
- All required fields marked with red asterisk + `aria-required`.
- Phone: 10 digits, Indian.
- Email: optional but validated.
- On success: confirmation card with reference no. (UUID v4 first 8 chars).

