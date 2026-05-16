---
name: Form UX patterns the user expects
description: For Indian-school admin forms, the user expects digits-only phone/Aadhaar inputs with exact-length validation, Title-Case name normalisation, dropdowns over free-text where finite options exist, and inline errors that don't auto-dismiss.
type: feedback
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
When asked to add validation to the school-management Admissions form, the user specified concrete rules without prompting for clarification:
- Phone / Alt phone: 10 digits exactly (Indian mobile format).
- Aadhaar: 12 digits exactly.
- Student / Father / Mother names: "camel case" (interpreted as Title Case — capitalised first letter of every word; standard Indian school register format).
- Religion: dropdown, "no number" — meaning enumerated options not free-text.

Implicit expectations that emerged from follow-up testing:
- Numeric inputs default-`0` are painful to edit (typing "500" produces "0500"). Initial state should be `""` (empty), treated as `0` on submit.
- Native HTML date input on Safari has internal mm/dd/yyyy spinbuttons that trap Tab. Auto-open the calendar via `showPicker()` so the user picks visually and Tab moves on.
- Inline errors are required, not toasts: when a CSV import has 5 bad rows, the user wants to see all 5 reasons + which column was bad on screen, not flash for 4 seconds and disappear.

**How to apply on this and similar admin projects:**
- Always default numeric form state to `""`, not `0`.
- For phone/aadhaar/account-number inputs, filter to digits-only on every keystroke (`digitsOnly()` helper) and cap maxLength at the exact target length.
- For person-name inputs, apply Title Case on blur (not on every keystroke — disruptive while typing).
- Replace any free-text "Religion / Designation / Type" field with a dropdown of the canonical Indian options.
- For DOB, bound `min` and `max` to a sensible range (today − 25 years to today for school students) and call `showPicker()` on focus.
- Show row-level errors in a sticky-header table inside the dialog, plus a top-level red banner for HTTP failures. Toasts are okay as a backup but never the primary surface.

The reusable helpers live in [frontend/src/lib/utils.ts](../../../Documents/GitHub/school-management/frontend/src/lib/utils.ts) (`RELIGIONS`, `toTitleCase`, `digitsOnly`, `dobBounds`) and [frontend/src/components/BulkImportDialog.tsx](../../../Documents/GitHub/school-management/frontend/src/components/BulkImportDialog.tsx).
