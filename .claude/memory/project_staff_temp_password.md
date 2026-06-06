---
name: project_staff_temp_password
description: Staff dual-credential temporary password + forgot/reset-password flow (Session 16)
metadata: 
  node_type: memory
  type: project
  originSessionId: ef13f4d1-04c7-4142-92f5-05bda9964d1f
---

Session 16 (2026-06-06) added two auth features, both deployed to PROD + TEST.

**Temporary password (migration 0010 — `staff.temp_password_hash` + `temp_password_set_at/by`):** a SECOND valid credential an admin/super-admin sets from the web Staff page to cover an absent teacher. It does NOT replace the teacher's own `password_hash` — the teacher keeps logging in normally; the temp password ALSO works until an admin clears it (no auto-expiry).
- Login (`backend/app/routers/auth.py`) accepts real-OR-temp: `ok_real = verify(password_hash)`, `ok_temp = verify(temp_password_hash)`. A temp login never triggers force-password-change and is logged `via=temp_password`.
- Endpoints: `POST /api/staff/{id}/temp-password` (body `{password}`, min 4) + `DELETE /api/staff/{id}/temp-password` (require_admin = admin or super_admin). `StaffOut.has_temp_password` drives the web UI badge.
- Web UI: "Temporary password (admin override)" section in the Staff edit dialog (`frontend/src/pages/Staff.tsx`). The Android/iOS apps need NO change — they just log in with email + temp password and get the teacher's exact scope/view.

**Forgot/reset password (migration 0011 — `password_reset_tokens`):** works for admin, super-admin, AND staff. `_resolve_reset_account` maps the hardcoded admin emails ([[project_prod_deployment_kisschool]]) + staff email/phone; `/auth/reset-password` updates the right account (admin/super_admin singletons or the staff row). Tokens are sha256-hashed, single-use, TTL `RESET_TOKEN_TTL_MINUTES` (30).
- **Requires SMTP** in `.env` (`SMTP_*`, Zoho `info@kisschool.in`) + `APP_BASE_URL=https://kisschool.in/admin` (prod) so reset links resolve. If SMTP is unset, the endpoint still returns the generic "if an account exists…" message (anti-enumeration) but no email sends — verify via the `password_reset_sent` vs `password_reset_smtp_unconfigured` log event.
- Web pages: `frontend/src/pages/{ForgotPassword,ResetPassword}.tsx` + login "Forgot password?" link. The ForgotPassword form must POST `{identifier}` (NOT `{email}` — that mismatch caused a 422; fixed in commit `60133ff`). The Android Login also has a Forgot-password link.
