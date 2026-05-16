---
name: No native HTML date input
description: school-management web bans `<input type="date">`; always use the shadcn `<DatePicker>` instead.
type: feedback
originSessionId: 567c8dd7-f9da-473d-b428-b40fbaf9720d
---
In the school-management frontend, never reach for `<Input type="date">` (or `<input type="date">`). Always use `DatePicker` from `@/components/ui/date-picker` (a popover-based component built on `@radix-ui/react-popover` + `react-day-picker@9` + `date-fns`).

**Why:** real users hit three bugs with the native picker on Chrome and Safari (macOS): popup not closing after a date is picked, year navigation broken, Safari mm/dd/yyyy subfield Tab-trap. The user explicitly asked for "modern calendar" in Session 6 and approved the migration of all 4 sites (Admissions DOB, StudentDetail DOB edit, Fees payment date, Attendance class date).

**How to apply:** For any new date field, import `DatePicker` from `@/components/ui/date-picker`. Pass `value` (ISO `YYYY-MM-DD` string), `onChange: (iso) => void`, and optionally `min` / `max` (also ISO). For DOB fields use `dobBounds()` from `@/lib/utils` for the today − 25 years window. Don't add `<Input type="date">` even as a placeholder; if I'm tempted, I should pause and use `DatePicker`.
