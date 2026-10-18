# 05 · Execution and Data Flow

> Index: [README.md](README.md) · Previous: [04-core-modules-and-business-logic.md](04-core-modules-and-business-logic.md) · Next: [06-configuration-and-environment.md](06-configuration-and-environment.md)

## 1. Backend startup (production)

```
 systemd: school-management.service            deploy/school-management.service
   After=network.target mysql.service
   User=school  WorkingDirectory=/opt/school-management/app
   EnvironmentFile=/opt/school-management/.env
   ExecStart=.venv/bin/gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 127.0.0.1:8000 --timeout 120
        │
        ├─ worker 1 ─┐   each worker imports backend/app/main.py independently:
        └─ worker 2 ─┤
                     │ 1. configure_logging()            logging_config.py — creates LOG_DIR, rotating app.log /
                     │                                    app.error.log (10 MB × 5), JSON by default, stdout handler
                     │ 2. Settings() reads .env           config.py — in prod the values arrive via systemd's
                     │                                    EnvironmentFile; defaults are dev placeholders
                     │ 3. engine = create_engine(...)     db.py — no connection yet (pool_pre_ping, recycle 1200 s)
                     │ 4. routers import                  pdf/render.py builds the Jinja environment at import;
                     │                                    WeasyPrint itself is imported lazily on first render
                     │ 5. app = FastAPI(lifespan=...)     middleware: RequestContextMiddleware, then CORSMiddleware
                     │                                    (added last → outermost); routers registered in the order
                     │                                    pdf_templates, pdf cache, marks_batches ×2, then the list
                     │ 6. lifespan startup                opens a session, _ensure_admin_seed + _ensure_super_admin_seed
                     │                                    (insert row id=1 with bcrypt(default password) if missing;
                     │                                    IntegrityError = the other worker won the race → fine), closes
                     │ 7. ready                           nginx proxies /api/ to :8000
```

Two details matter: the admin seed runs **per worker** and is race-safe; and the
trailing block in `main.py` that would mount `/static` and `/` if an `index.html`
existed three directories up is a leftover from the single-file era and never fires on
the server (see [08](08-risks-limitations-and-improvements.md)).

Local dev is the same minus systemd: `uvicorn app.main:app --reload` from `backend/`
with a `backend/.env`.

## 2. Anatomy of one request

```
 browser ─▶ nginx  /school/api/students?class=5th   (TEST)  or  /api/students?class=5th  (PROD)
             │  proxy_pass http://127.0.0.1:8000/api/  — prefix stripped, X-Forwarded-* added
             ▼
 CORSMiddleware (no-op for same-origin)
 RequestContextMiddleware                                  middleware.py
   rid = X-Request-ID header or uuid4()[:12]
   best-effort decode of the token (header or ?token=) → contextvars request_id / user_sub / user_role
   start timer
   ▼
 FastAPI routing → dependency resolution                   deps.py
   db_dep → get_db() → SessionLocal()                      one synchronous Session per request
   current_user → "Authorization: Bearer …" → decode_token → CurrentUser
                  (allowed_classes passed through expand_classes)     401 if missing/invalid
   require_admin / require_super_admin                      403 on role mismatch
   Pydantic body/query models                              422 before the handler runs
   ▼
 handler (routers/students.py::list_students)
   assert_class_allowed(user, "5th")                       403 "Class not in scope" for staff outside scope
   build SELECT, apply soft-delete filter, count, page
   per-row decoration (_to_out → 3 COUNT queries per student for document flags; batch pending-edit lookup)
   return StudentPage                                      response_model serialises
   ▼
 finally: session closed; access log {method, path, status, duration_ms, client}; X-Request-ID set
```

### Error propagation

| Where | What happens | Client sees |
|---|---|---|
| Dependency (`deps.py`) | `HTTPException(401/403)` | `{"detail": "Missing token" / "Admin only" / "Class not in scope"}` |
| Pydantic validation | `RequestValidationError` | 422 with a `detail` array of field errors |
| Handler business rule | `HTTPException(400/404/409/410/503)` with a string or dict `detail` | e.g. 409 `"Roll number 14 in 5th is already used by …"`, 409 `"Batch is submitted (locked)…"`, 410 for retired PDF kinds |
| Handler raises anything else (e.g. an `IntegrityError` not caught) | propagates through the middleware (logged as `request failed` with traceback), then `unhandled_exception_handler` in `main.py` logs `unhandled exception` and returns 500 `{"detail": "Internal server error"}` | generic 500; look up the `request_id` in `app.error.log` |
| After `db.commit()` | the write is durable even if a later step (notification, logging) fails; notification helpers are wrapped so they cannot raise, and logging uses only non-reserved `extra` keys for exactly this reason | — |
| Session cleanup | `get_db`'s `finally: db.close()` discards any uncommitted changes | — |

Side effects always follow the same order inside a mutating handler:
**validate → mutate → `db.commit()` → `broker.publish(...)` → `notify_*(...)` → `log.*`**.
Keep it; it is what makes failures after the commit harmless.

## 3. Key flows

### 3.1 Login and identity

```
 POST /api/auth/login {identifier, password}                       routers/auth.py::login
   identifier == SUPER_ADMIN_EMAIL ──▶ super_admin_auth row (seeded if absent) ──▶ bcrypt verify
   identifier == ADMIN_EMAIL       ──▶ admin_auth row                         ──▶ bcrypt verify
   contains "@"                    ──▶ staff by lower(email), status != deleted
   else                            ──▶ staff by digits-only phone (then a normalising scan)
       ok_real = verify(password_hash) ; ok_temp = verify(temp_password_hash)
   classes = expand_classes([staff_classes…])      "All" → 15 concrete names
   token = create_token(sub, role, name, allowed_classes, allowed_menus)   HS256, exp = now + JWT_EXPIRY_HOURS
   → LoginResponse {token, role, name, allowed_classes, allowed_menus, force_password_change}
```

Web (`frontend/src/pages/Login.tsx`): stores the token in `sessionStorage` (`kis_token`)
and the user in `kis_user`, optionally the identifier in `localStorage`, shows a toast if
`force_password_change`, navigates to `/dashboard`. Android (`LoginViewModel` →
`TokenStore`): routes to the change-password screen when the flag is set. Every later
request re-derives identity from the token only — there is **no server-side session**
and `POST /auth/logout` merely logs.

### 3.2 Student edit (approval queue)

```
 PATCH /students/{id} {fields…}                     routers/students.py::update_student
   diff_fields = fields whose value actually differs
   super_admin ─▶ setattr…, recompute admission_id, uniqueness check, commit, publish students
   admin/staff ─▶ 409 if a pending request exists
              ─▶ pre-flight uniqueness on the prospective values (so the 409 comes now, not at approval)
              ─▶ INSERT student_edit_requests {changes: {field: {old, new}}, requested_by, role}
              ─▶ commit → publish edit_requests + students → notify_student_edit_request (approver inbox)
              ─▶ returns the UNCHANGED student decorated with has_pending_edit = true
 super-admin later: POST /admin/edit-requests/{rid}/approve      routers/edit_requests.py
   _apply_diff: StudentUpdate(**new_values) re-validates types; setattr; recompute admission_id; uniqueness
   req.status = approved; commit; publish; notify_request_outcome → requester's email (looked up by display name)
```

The UI (`Students.tsx`, `StudentDetail.tsx`, Android `EditStudentScreen`) hides the
edit action while `has_pending_edit` is true.

### 3.3 Soft delete

```
 active ──(admin/staff DELETE /students/{id} or /staff/{id})──▶ pending_delete
 active ──(super-admin DELETE)────────────────────────────────▶ deleted
 pending_delete ──(POST /admin/deletion-requests/{kind}/{id}/approve)──▶ deleted
 pending_delete | deleted ──(…/restore, admin or super-admin)──▶ active (audit columns cleared)
 deleted ──(DELETE /admin/deletion-requests/{kind}/{id}, super-admin)──▶ row removed, FK CASCADE wipes children
```

Default listings filter `status != deleted`; `pending_delete` rows stay visible with a badge.

### 3.4 Attendance save

```
 PUT /attendance {class_name, date, records: {student_id: "P|A|L|H"}, is_holiday}
   find-or-create attendance(class_name, date)
   delete ALL existing attendance_records for the day; flush
   if not is_holiday: insert one record per entry (bad status → 400)
   commit → publish dashboard "attendance_changed"
 DELETE /attendance?class=&date=  → delete the parent row (records cascade) — "un-mark the day"
 GET /attendance/marked-dates?class=&from=&to= → {dates: [...non-holiday], holidays: [...]}  (one call per month)
```

### 3.5 Marks: batch lifecycle and results

```
            POST /marks/batches (upsert)                     POST /{id}/submit
  (none) ───────────────────────────▶ draft ──────────────────────────────▶ submitted (locked)
            creates batch + rows;        ▲                                      │
            re-save updates rows,        │ super-admin approve                  │ admin/staff POST /{id}/request-edit {reason}
            deletes rows the client      │ POST /admin/marks-edit-requests/{rid}/approve
            omitted                      └──────────────────────────────────────┤ (pending request; 409 if one exists)
                                                           reject → stays submitted; last_rejection shown to teacher
  super-admin: may save/submit a submitted batch directly; may NOT file a request (403)
```

Rows live in `marks` with `batch_id` set; `UNIQUE(batch_id, student_id)` makes re-saves
updates rather than duplicates. Results:

```
 GET /marks/results?class=&session=&scope=              routers/marks.py::class_results
   subjects  = class_subjects WHERE class_name=…  (components eager-loaded)
   students  = students WHERE class_name=… AND status != deleted  (roster order roll_no, name)
   marks     = marks WHERE class_name=… AND session=…            (drafts included; batch status ignored)
   aggregate_class_results(...)                         services/results.py — pure
     per subject: in-scope components by term → scope_max; per student: obtained, pct, grade, status
     grand total over subjects with max > 0
   → ClassResultsOut {subject_columns, students[{subjects[], total_obtained, total_max, percentage, grade}]}
```

Legacy marks whose `exam_type` is not a current component name are silently ignored.

### 3.6 Templated PDF render with cache

```
 POST /pdf/templates/{id}/render {student_ids, force}         routers/pdf_templates.py → pdf/render_or_cache.py
 for each student:
   1. student must exist and be in the template's class                      else status=error
   2. gather inputs: pdf_student_data row; for report-card also marks (student × class × session)
      and class_subjects(+components); scope = scope_from_term(template.term)
      source_hash = sha1(sorted "subject|exam_type|marks|max_marks" lines + sorted student-data JSON)
   3. unless force: SELECT pdf_cache WHERE kind, student_id, template_id, template_version, source_hash
      hit → {status: cached, pdf_id}
   4. build payload: builder.build_report_card_payload / build_pseb_admit_payload → Pydantic model
      (ValidationError/ValueError → status=error with the message, e.g. missing PSEB regNo)
   5. render_pdf(kind, payload.model_dump(by_alias=True, mode="json")) → Jinja2 → WeasyPrint → bytes
   6. upsert pdf_cache row at (kind, student_id, template_id, template_version), set source_hash; commit
      → {status: rendered, pdf_id}
 download: GET /pdf/cache/{pdf_id}/inline?token=…  (frontend/src/lib/pdf.ts::downloadCachedPdf)
```

Editing the template bumps `version` (new cache key); editing marks or per-student data
changes `source_hash` (cache miss). Both invalidations are implicit — nothing deletes
old rows, so `pdf_cache` only grows (see 08).

### 3.7 Ad-hoc PDF

`POST /pdf/{kind}` → `SCHEMA_BY_KIND[kind].model_validate(body)` (422 on failure) →
`render_pdf` → `application/pdf` response, `Content-Disposition: inline`. The frontend
helper `downloadPdf` turns the blob into a download. `report-card` and
`pseb-admit-card` are refused with 410.

### 3.8 Forgot / reset password

```
 POST /auth/forgot-password {identifier}
   resolve account (same lookup order as login) → None → generic 200 message anyway
   mark earlier unused tokens used; INSERT password_reset_tokens {token_hash = sha256(raw), expires_at = now + TTL}
   email `${APP_BASE_URL}/reset-password?token=<raw>` via mailer (EmailNotConfigured → logged, still 200)
 POST /auth/reset-password {token, new_password}
   lookup by sha256(token); reject used/expired; update the matching singleton or staff row;
   staff.force_password_change = False; token.used_at = now
```

### 3.9 Bulk CSV import (all five entities)

```
 POST /<entity>/bulk-import (multipart file)
   rows = read_csv(file)             utf-8-sig, DictReader
   for each row (numbered from 2): validate with must_*/opt_*/parse_date_field; collect FieldError → errors[]
   any errors → {inserted: 0, errors, aborted: true}   NOTHING written
   else add all prepared rows; ONE commit; publish; {inserted: N, errors: [], aborted: false}
```

`BulkImportDialog.tsx` keeps the error table on screen and offers an error-report CSV.
Staff import additionally returns one-time `credentials[]`.

## 4. Realtime: from a write to a refreshed screen

```
 handler commits ─▶ broker.publish("students", "upsert", id=…)        events.py
                      for every asyncio.Queue subscribed to "students" in THIS worker process: put_nowait
                      (queue full at 100 → event dropped silently)
 GET /api/stream/students?token=…  (opened by useSSE on page mount)    routers/stream.py
   EventSourceResponse yields {"data": "<json>"} per message, ping every 15 s; nginx buffering off, 24 h timeout
 browser EventSource.onmessage ─▶ queryClient.invalidateQueries(["students"]) ─▶ TanStack refetches
```

Consequence of `-w 2`: a browser whose SSE connection landed on worker A receives
nothing for writes handled by worker B. Users still see fresh data on the next
navigation or after `staleTime` (30 s) when the query re-mounts, which is why the
limitation has been tolerable.

## 5. Frontend startup and navigation

```
 index.html (no-cache meta, Google Fonts) ─▶ main.tsx
   imports packages/design-system/tokens.css, styles/globals.css, lib/i18n (locale from localStorage)
   QueryClient {staleTime 30 s, retry 1, no refetch on focus}
   <BrowserRouter basename = import.meta.env.BASE_URL without trailing slash>   ("/school/admin" or "/admin")
   <App>: useVersionCheck() → fetch `${BASE_URL}version.json` now and every 5 min while visible;
          mismatch with __BUILD_ID__ → location.replace(url + "?_v=<ts>")
   <Routes>: public /login, /forgot-password, /reset-password
             <ProtectedRoute><Layout/></ProtectedRoute> wraps everything else;
             each child route adds its own ProtectedRoute with menuKey / adminOnly / superAdminOnly
             unknown path → /dashboard
 Layout: Sidebar + TopNav (mode from localStorage kis.nav.mode), user menu, LocaleSwitch, Outlet
 Page: useQuery(...) per dataset, useMutation(...) per action, useSSE(channel, keys)
 axios 401 anywhere → clear token → location.href = `${BASE_URL}login`
```

## 6. Android launch

```
 KisApp.onCreate ─▶ AppContainer(context)   TokenStore (EncryptedSharedPreferences), OkHttp (+Bearer interceptor,
                                             401 → clear + authExpired), Retrofit(BuildConfig.API_BASE_URL), repos
 MainActivity.setContent ─▶ KISTheme ─▶ UpdateGate(appUpdateRepo)
   fetch BuildConfig.APP_VERSION_URL (downloads/app-version*.json); null on any failure → fail open
   installed < min_version_code → blocking dialog with Download; < latest → optional prompt
   ─▶ AppNav(start = login | change-password (forced) | home)
   LaunchedEffect collects authExpired → navigate to login, clear back stack
```

## 7. Deploy pipeline (what `/deploy-test-all` and `/deploy-prod-all` do)

```
 scripts/deploy/<env>/deploy-all.sh → env.sh (server, key, domain, path knobs) → common/lib.sh::deploy_full
   ssh_preflight                      key + host reachable
   local_python_lint                  ast.parse every backend/*.py
   local_frontend_build               npm ci && VITE_BASE=… VITE_API_URL=… npm run build   (tsc -b && vite build)
   remote_snapshot                    tar app/ → backups/app_<ts>.tgz ; mysqldump → backups/db_<ts>.sql.gz ; prune > 30 d
   push_backend / push_frontend       rsync --delete (backend excludes .venv, tests, caches)
   remote_install_and_restart         venv, pip install -r requirements.txt, source .env, alembic upgrade head,
                                      chown, systemctl restart, is-active check
   health_wait                        curl https://<domain><HEALTH_PATH> up to 8 × 5 s
   on failure at install or health    remote_rollback(<ts>): stop, replace app/, start   (DB is NOT rolled back)
```

Frontend-only and backend-only variants skip the other half; the public site has its
own `deploy-public-site.sh`; the APK goes through `upload-apk.sh`, which verifies the
APK is downloadable (HTTP 200) **before** publishing the force-update manifest.

## 8. Shutdown

`systemctl stop/restart` sends SIGTERM to gunicorn, which stops accepting connections
and lets workers finish in-flight requests (gunicorn's graceful timeout, default 30 s);
the FastAPI `lifespan` logs `shutdown`. Open SSE connections are cut; browsers'
`EventSource` reconnects automatically once nginx can reach the new workers. There is
no in-memory state worth persisting — the broker queues are transient by design — and
no scheduled jobs run inside the process (APScheduler is installed but unused).

> Next: [06-configuration-and-environment.md](06-configuration-and-environment.md) — every knob and where it is set.
