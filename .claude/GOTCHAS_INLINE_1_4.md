# Gotchas — items #1-#4 (archived from CLAUDE.md inline list)

These were the four oldest items in the inline gotchas list; they're still
true and load-bearing but rotated out of CLAUDE.md to keep the inline list
under 15 items. All four predate the Session 13 sweep.

---

1. **React Router needs `basename` when the SPA isn't at root.** Without it, `<NavLink to="/admissions">` produces `/admissions` (which nginx routes to uploadmytds's catch-all) instead of `/school/admin/admissions`. [frontend/src/main.tsx](../frontend/src/main.tsx) reads `import.meta.env.BASE_URL` and feeds it to `<BrowserRouter basename={...}>`. The `api.ts` 401 redirect also derives `/school/admin/login` from `BASE_URL` — never hardcode `/login`. Same code Just Works if you ever deploy to root.

2. **Empty array `[]` is truthy with `??`.** Admin's JWT has `allowed_classes: []` (full access marker). Code like `user?.allowed_classes ?? CLASSES` keeps the empty list and dropdowns render zero items. Use `user?.allowed_classes?.length ? user.allowed_classes : CLASSES` everywhere a class dropdown is filtered.

3. **Number inputs default-`0` = leading-zero edit pain.** With `value={form.annual_fee}` initialised to `0`, typing "500" produces "0500" because state is "0" not "". Fix: use `""` as the initial state for numeric form fields, treat empty as `0` at submit (`Number(form.annual_fee) || 0`). For edit pages, also display `""` when the existing value is `0` so users don't have to delete a leading zero before typing. **Session 13 update:** the new `NumberField` component (`frontend/src/components/ui/number-field.tsx`) bakes this contract in plus hard-clamping; prefer it over raw `<Input type="number">` for any bounded numeric field.

4. **Bulk-import errors in the dialog (not the toast).** Toasts auto-dismiss after 4s; per-row CSV errors need to stay on screen so the user can read each reason and fix the file. [BulkImportDialog](../frontend/src/components/BulkImportDialog.tsx) renders a sticky-header table of `(row, reason, offending value)` plus a top-level red banner for HTTP/network failures, and the Upload button morphs to "Try again" so users iterate without closing the dialog. Also includes a "Download error report" CSV with all failed rows + reasons + original column data.
