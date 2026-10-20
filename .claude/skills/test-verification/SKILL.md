---
name: test-verification
description: Verify a deploy of the KIS portal — on-box server smoke (26 checks, TEST or prod), API and headless-Chrome checks as super-admin, admin and a teacher, and a review of the owner's own TEST run (nginx log + sign-in sessions) before go-live; logins only as environment variables. Use after every deploy and before committing or going live.
---

# TEST verification

## When to Use
- Right after deploying to TEST (`deploy-all.sh`, usually from the working copy — Gotcha #23), before committing ("code → deploy TEST → test → commit").
- When the owner asks to "test it by UI" or sends logins for UI testing.

## Inputs / Modes
- `smoke` — server smoke only (no logins needed; tokens are minted on the box with TEST's own secret and never printed).
- `api` — smoke + API checks (needs `KIS_U1` super-admin identifier + `KIS_PW`).
- `full` (default) — smoke + API + browser checks.
- `review` — before a go-live, review the owner's own TEST run instead of re-testing: errors, refused requests and sign-in sessions since their testing started (step 5).
- `prod-smoke` — after a prod deploy, the same smoke on prod (step 1 with prod's user, paths and port).
- Logins: `KIS_U1` (super-admin email), `KIS_U2` (admin email), `KIS_PW` (password). **Pass them inline as env vars only — never write them to a file, the repo or memory.** Teacher checks pick an active teacher through the API and use the TEST temporary password (every active TEST staff member has one; value user-known).

## Steps
1. **Server smoke (on the box):**
   ```
   scp -i ~/.ssh/enamfoss_prod .claude/skills/test-verification/scripts/smoke_results.py root@69.62.72.137:/tmp/smoke_results.py
   ssh -i ~/.ssh/enamfoss_prod root@69.62.72.137 "chmod 644 /tmp/smoke_results.py; sudo -u school-test bash -c 'set -a; . /opt/school-management-test/.env; set +a; cd /opt/school-management-test/app && PYTHONPATH=/opt/school-management-test/app .venv/bin/python /tmp/smoke_results.py'"
   ```
   Expect `26/26 passed` (health, sessions, meta, results ×3 scopes + permissions, report-card resolve/roster/render/download, render job + ZIP, stale-save 409, revision guard, old-app prune guard, unknown session 422, session defaults). Writes only regenerable rows (one cached card, one 2-card job).
2. **API checks (from the Mac):**
   `KIS_U1=… KIS_PW=… python3 .claude/skills/test-verification/scripts/api_dashboards.py` (class-summary scope/order/range/422, marks batches summary, fees 403 for staff) and `… scripts/api_stay_signed_in.py` (refresh rotation, lost-response grace, replay → family revoked, logout, devices list, web cookie attributes). Both print only PASS/FAIL lines — no names, no tokens.
3. **Browser checks:** one-time setup `mkdir -p <scratch>/uitest-deps && cd <scratch>/uitest-deps && npm i playwright-core@1.50.1` (uses the installed Google Chrome via `channel: "chrome"`). Run each script with `PW_DEPS=<scratch>/uitest-deps SHOTS=<scratch>/shots KIS_U1=… KIS_U2=… KIS_PW=… node scripts/<name>.mjs`:
   - `ui_results.mjs` — super-admin + admin: Results (scopes, each-exam, CSV, print), Report cards tab, Templates, Sessions pre-fill, Punjabi toggle, phone width, admin blocked from super-admin pages.
   - `ui_teacher.mjs` — a teacher (found via the API): own classes only, report-card controls hidden, Marks Entry locked batch, admin pages blocked.
   - `ui_marks.mjs` — Marks Entry: integer-only input, unsaved-change prompt (never saves).
   - `ui_dashboard.mjs` — dashboard pie → Pending list → Back, class-wise chart, teacher sees no pie.
   - `ui_remember.mjs` — Remember me: new tab stays signed in, silent renewal, Log out ends it, no Remember me = old behaviour.
4. Read 1–2 key screenshots before reporting; report pass/fail per step and any browser errors.
5. **Review the owner's TEST run (`review`):** `bash scripts/deploy/test/check-logs.sh 1d` (crashes, restarts — tracebacks section is not time-filtered), then the real request log `zcat -f /var/log/nginx/access.log /var/log/nginx/access.log.1 | grep "/kisschool/api/"` filtered to status ≥ 400 in their time window, with path + user agent (`okhttp` = app). Map refusals to accounts via `device_sessions` (`SELECT id, platform, account_type, account_ref, created_at, last_used_at, rotated_at IS NOT NULL, revoked_reason FROM device_sessions ORDER BY created_at` — UTC times) and `staff.allowed_menus`; print IDs, never names. A 403 for a menu the account holds is a regression (2026-10-20: Fees-menu staff refused `GET /fees`).
6. **Prod smoke (`prod-smoke`):** copy `smoke_results.py` to the box and run `sudo -u school bash -c 'set -a; . /opt/school-management/.env; set +a; cd /opt/school-management/app && PYTHONPATH=/opt/school-management/app .venv/bin/python /tmp/smoke_results.py http://127.0.0.1:8000/api'` — expect 26/26 (writes one cached 8th-class card and a 2-card render job; every save it attempts is refused by design).

## Gotchas / FP patterns
- **Never wait for `networkidle`** on pages with live updates (Dashboard, Marks Entry): the SSE stream keeps a request open → timeout. Use `domcontentloaded` + a fixed wait.
- **Chart.js animates** bars from zero/left: wait ~8 s after a period switch before a screenshot, or flat/squeezed bars look like a bug.
- Marks Entry's class/subject/test pickers have no ids/labels — select `main button[role="combobox"]` by position (0 class, 1 subject, 2 test) and match options by prefix (labels include Punjabi/max marks).
- Remark inputs have no `type="text"` attribute — don't select them with `input[type="text"]`.
- The header Log Out is `header button` filtered by text; a hidden sidebar copy exists — `getByRole(...).first()` can pick the hidden one.
- Running the smoke as `python /tmp/x.py` needs `PYTHONPATH=<app dir>` (Python adds the script's dir, not the cwd).
- TEST's data is a prod clone: today's attendance is usually empty there, so "today" views show everything pending — not a bug.

## Expected Output
A PASS/FAIL list per step (smoke N/26, API N/N, browser steps), screenshots under the scratch `SHOTS` dir, and a short user-facing summary of anything that failed.
