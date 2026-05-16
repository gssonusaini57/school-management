# Gotchas Archive — Items 1–6 (Foundational, post-migration)

These were the first six gotchas captured after the Firebase → FastAPI/MySQL migration. They are still load-bearing but are now standard parts of the architecture; the active CLAUDE.md keeps a more recent set inline.

---

1. **Single-process broker.** [backend/app/events.py](../backend/app/events.py) uses an in-memory pub/sub. With `gunicorn -w 2` the SSE only fires from the worker that handled the mutation. Acceptable for a school's load (few concurrent users); upgrade to Redis if you ever scale workers.

2. **Admin password seed.** `_ensure_admin_seed(db)` in [backend/app/routers/auth.py](../backend/app/routers/auth.py) creates row id=1 with bcrypt(`ADMIN_DEFAULT_PASSWORD`) on first request OR app startup (called from `lifespan`). Don't rely on Alembic for the seed — keep it in code.

3. **Staff access code lookup is `last4`-narrowed.** Login query filters by `access_code_last4 = code[-4:]` then bcrypt-verifies each candidate. Avoids loading every staff row into memory while keeping codes hashed at rest.

4. **Files served via `/inline?token=`.** Browsers cannot put `Authorization` headers on `<img src>`. The `/api/files/.../inline` endpoint accepts the JWT as a query string (same Bearer JWT, just a different transport). Don't expose this URL pattern publicly without a token.

5. **Vite `base: "/school/"`.** All built asset URLs are prefixed `/school/...`. This means `npm run dev` also runs at `http://localhost:5173/school/`, NOT root. The dev proxy still maps `/api` → `localhost:8000` because we hit the proxy from a fully-qualified URL.

6. **CORS not needed in prod.** Frontend and API are same-origin (`expressonly.in`). The `CORS_ORIGINS` env var only matters during local dev when Vite proxies fail or you call FastAPI directly.
