---
name: project_stay_signed_in
description: Session 19 "stay signed in" design — device_sessions refresh tokens (30 d sliding / 180 d absolute, rotation + replay detection), web Remember-me HttpOnly cookie, Android fingerprint/face App lock with several saved accounts. Live on prod since 2026-10-20 (0021, app 1.3.4).
metadata:
  type: project
---

**Why:** the owner complained of typing the password "every time" — access JWTs last 1 hour (`JWT_EXPIRY_HOURS=1` on both instances) and the server kept no session state, so the app and website logged everyone out hourly. Owner decisions (2026-10-19): several saved accounts per phone with a switcher, 30 days of use before the password is needed, a "Sign in faster next time?" popup after a password login, website stays signed in with Remember me.

**What exists (TEST, commits b211a3e / c686312 / 6916304 / a71d7b7):** table `device_sessions` (migration 0021); `/auth/login` + `remember`/`device`; `/auth/refresh` rotates (replay revokes the family; 60-s grace for a lost response); `/auth/logout` (Bearer optional); `/auth/sessions`; admin `DELETE /staff/{id}/sessions`; revocation on password change/reset, temp-password clear, staff deletion; 429 after 10 failed logins per identifier per 15 min. Web: HttpOnly `kis_refresh` cookie, `Path` = `AUTH_COOKIE_PATH` (TEST `.env` `/kisschool/api/auth`, prod default `/api/auth`). Android 1.3.3: BiometricPrompt (`BIOMETRIC_WEAK | DEVICE_CREDENTIAL`) on open and after 15 min away, saved accounts (org.json in the encrypted prefs), Switch account, Settings (theme, App lock, signed-in devices).

**How to apply:** rules are CLAUDE.md Gotcha #25. The owner's phone test on TEST passed (2026-10-20). Pending: nginx `limit_req` on login/refresh; `AUTH_COOKIE_PATH` into `deploy/.env.example` + provision step 04; shorten `JWT_EXPIRY_HOURS` once every phone runs 1.3.x; a web "signed-in devices / sign out lost phone" page; set `CORS_ORIGINS` explicitly before the prod deploy. Related: [[project_staff_temp_password]], [[project_staff_auth_revamp]], [[project_android_teacher_app]].

**Live on prod since 2026-10-20 11:33** (`339c013`, schema 0021, app 1.3.4 build 25).
