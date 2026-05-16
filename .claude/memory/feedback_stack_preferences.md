---
name: Stack preferences for new code
description: User prefers modern, well-maintained TypeScript-first frontend stacks and FastAPI on the backend; bcrypt for any credential at rest; SSE over WebSockets for low-volume realtime.
type: feedback
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
When proposed multiple architectural options for the school-management migration, the user picked:

- **Backend:** FastAPI (over Flask, Django, Node).
- **Frontend:** React + Vite + TypeScript (declined Angular even though they know it; declined "keep single index.html"; declined multi-page vanilla split).
- **UI:** Tailwind + shadcn/ui (over React-Bootstrap, MUI). Acknowledged not knowing the libraries and asked for explanation; chose the modern option after I explained.
- **Routing:** Sub-routes per resource (over single SPA with tabs).
- **Server state:** TanStack Query.
- **Forms:** react-hook-form + Zod.
- **Realtime:** Server-Sent Events (over WebSockets, over polling, over removing realtime).
- **Auth:** bcrypt for both admin password AND staff access codes (declined the "hash admin only" middle option).
- **Database:** Switched from initial Postgres pick to MySQL when I pointed out uploadmytds already runs MySQL on the shared VPS.

**Why:** Lead with the recommendation + tradeoffs, especially when the user says they don't know the library. Don't assume framework familiarity; explain.

**How to apply:** For NEW work, default to: FastAPI / React+Vite+TS / Tailwind+shadcn / TanStack Query / react-hook-form+Zod / SSE / bcrypt / MySQL (when sharing the VPS) or Postgres (greenfield). Don't propose vanilla HTML, jQuery, or Bootstrap unless the user explicitly asks for "preserve the current look".
