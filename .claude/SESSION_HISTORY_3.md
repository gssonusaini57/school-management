# Session History — Session 3 (archived from CLAUDE.md)

## Session 3 — 2026-05-07 (mid-day) · Firebase → FastAPI/MySQL migration scaffold
**Focus:** Rip out Firebase, build FastAPI backend + React frontend, no deploy yet.

**What was created:**
- **Backend:** Full FastAPI app under [backend/](../backend/) — 8 SQLAlchemy models, 8 Pydantic schema modules, 11 routers (auth/students/files/attendance/marks/fees/notices/staff/reports/stream/health), `app/events.py` SSE broker, `app/security.py` (JWT + bcrypt), `app/deps.py` (current_user / require_admin / class scope), Alembic migration `0001_initial`, `requirements.txt`. Lifespan-seeded admin password (bcrypt of `admin123` on first boot).
- **Frontend:** Full React + Vite + TS + Tailwind + shadcn/ui app under [frontend/](../frontend/) — 12 pages (Login, Dashboard, Admissions, Students, StudentDetail, Attendance, MarksEntry, MarksResults, Fees, Notices, Staff, Reports), Layout + ProtectedRoute, 12 shadcn UI primitives copied in, TanStack Query + EventSource for SSE, react-hook-form patterns, axios with Bearer interceptor + 401 redirect, client-side image compression preserved from old code.
- **Deploy artifacts** (used in Session 4): [deploy/school-management.service](../deploy/school-management.service), [deploy/nginx.school.conf](../deploy/nginx.school.conf), [deploy/.env.example](../deploy/.env.example), initial deploy script.
- **Cleanup:** Deleted `firebase.json`, `.firebaserc`, `firestore.rules`, `storage.rules`, `deploy-rules.bat`. Archived old `index.html` to [_archive/index.firebase.html](../_archive/index.firebase.html).

**Verification:** Backend AST-parses clean. Frontend `npm run build` passes (~622 KB JS / 203 KB gz). No deploy yet — that became Session 4.
