---
name: staff-auth-revamp
description: Session 10 (2026-05-16) — replaced staff access_code with email/phone+password; unified login form (no role tabs); auto-generated Employee IDs; ChangePassword screens on Android+iOS; admin/superadmin identifiers now admin@kis.com / superadmin@kis.com.
metadata: 
  node_type: memory
  type: project
  originSessionId: b674257f-abf8-4261-95d6-22d3609faf67
---

**Fact:** Session 10 replaced the staff `access_code` auth model with `email + password` across backend, web, Android, and iOS. Login is now a single form accepting `{identifier, password}` where identifier may be `admin@kis.com`, `superadmin@kis.com`, a staff email, or a staff phone (digits-normalized). No role tabs on the login page. Migration `0005_staff_auth` adds `staff.email` (UNIQUE) / `employee_id` (UNIQUE, `KIS/EMP/{year}/{seq:04d}`) / `password_hash` / `force_password_change` and drops `access_code_hash` / `access_code_last4`. Staff page redesigned: full-width data table with `Add staff` + `Bulk import` header buttons; form opens in a Dialog; Employee ID auto-generated server-side and shown once with initial 6-digit password. PATCH supports `reset_password: bool`. New `POST /staff/change-password` endpoint. Android bumped to v1.1.0 build 3 with a new `ChangePasswordScreen`; iOS got a `ChangePasswordView` (source only — no Apple Dev acct yet). Both apps route through change-password when `force_password_change=true`.

**Why:** User wanted (a) the Staff page revamped — directory as data table, form as popup, email + auto Employee ID, and (b) a simpler unified login. The access-code model conflated credential issuance with directory management, gave staff no recovery path, and required printing/sharing 6-digit codes per phone. Email+password lets staff actually own their credential, and the unified `identifier` field removes the cognitive load of picking the right role tab.

**How to apply:**
- Never re-introduce `access_code` fields or `role` in the login request. The `LoginRequest` schema is `{identifier, password}`.
- Hardcoded admin emails live in [backend/app/routers/auth.py](../../../Documents/GitHub/school-management/backend/app/routers/auth.py) as `ADMIN_EMAIL` / `SUPER_ADMIN_EMAIL`. To change them, edit the constants — no DB migration needed (admin/super_admin auth tables are singletons keyed by id=1).
- New staff creation auto-assigns Employee ID via `_next_employee_id(db, year)` in [backend/app/routers/staff.py](../../../Documents/GitHub/school-management/backend/app/routers/staff.py) — matches the `_compute_admission_id` pattern in students.py.
- Frontend canonicalizes legacy class spellings (`LKG` ↔ `L.K.G`) so old data ticks correctly in the Edit dialog; see `canonicalizeClass` in [frontend/src/pages/Staff.tsx](../../../Documents/GitHub/school-management/frontend/src/pages/Staff.tsx).
- Maintenance script for fixing legacy creds: [backend/scripts/fix_staff_credentials.py](../../../Documents/GitHub/school-management/backend/scripts/fix_staff_credentials.py). Run from `/opt/school-management/` (not `/opt/school-management/app/`) so the `.env` is picked up by pydantic-settings.
- `email-validator==2.2.0` must stay in [backend/requirements.txt](../../../Documents/GitHub/school-management/backend/requirements.txt) — Pydantic's `EmailStr` needs it at import time.
- Related: [[school-management-deployed]] for the live identifier/password reference, [[android-teacher-app]] for the rebuilt APK at /school/downloads/kis-attendance.apk.
