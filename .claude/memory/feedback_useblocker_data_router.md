---
name: useblocker-needs-data-router
description: "React Router v7's useBlocker throws on the classic BrowserRouter; only works under createBrowserRouter + RouterProvider. Bit us in the school-management portal (StudentDetail page went blank)."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 72d7a2e8-22f7-47ff-8eaa-30b034aaedba
---

`useBlocker` (and `usePrompt`, `useFetchers` for some hooks) from react-router-dom v7 require a **data router** — i.e. `createBrowserRouter` + `RouterProvider`. They throw on mount when used inside the classic `<BrowserRouter>` wrapper, which crashes the page entirely (blank white screen).

**Why:** `useBlocker` hooks into the router's transition state which only exists in data routers. Classic routers don't expose it.

**How to apply:**
- In school-management's [frontend/src/main.tsx](../frontend/src/main.tsx), the app uses `<BrowserRouter basename={basename}>`. Do NOT call `useBlocker` anywhere downstream from that until/unless someone migrates to `createBrowserRouter`.
- For "guard unsaved changes when leaving" UX without a data router, use this trio instead:
  1. `window.addEventListener("beforeunload", …)` for browser refresh/close.
  2. Wrap the in-app Back / Cancel buttons with `window.confirm()` and short-circuit.
  3. Sidebar / `<NavLink>` clicks are NOT interceptable without a data router — accept that gap or migrate the router.

Tagged so the bug shows up in `git log`: Session 11 (2026-05-17), shipped + reverted in the same session. See [[user_profile]] for the stack context.
