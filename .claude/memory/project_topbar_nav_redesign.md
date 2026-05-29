---
name: project-topbar-nav-redesign
description: "Session 12 dual-mode navigation on the React admin portal — horizontal top bar with section dropdowns (default) toggleable to legacy left sidebar via hamburger; `localStorage` persisted."
metadata: 
  node_type: memory
  type: project
  originSessionId: b9349413-a203-442a-ad69-8a0001e39e16
---

Session 12 (2026-05-17). The admin portal at `/school/admin/` no longer has a fixed left sidebar by default. Instead:

- **Default (desktop):** slim white topbar (16 px) + dark `bg-deep-indigo` horizontal nav strip (48 px) with 5 section dropdowns (Main / Academic / Administration / Stationery / Resources). Each dropdown opens via shadcn `DropdownMenu`. Total chrome height: 64 + 48 = 112 px → `<main>` uses `md:pt-28`.
- **Toggle:** hamburger in the slim topbar. On desktop it flips between `'topbar'` and `'sidebar'` modes (preference persisted to `localStorage` key `kis.nav.mode`). On mobile it opens a drawer over the content.
- **Sidebar mode (desktop):** the legacy 256 px dark left aside reappears; slim topbar shifts to `md:left-64`; `<main>` gets `md:ml-64` instead of `md:pt-28`.
- **Mobile:** no horizontal nav ever. Hamburger always opens the drawer. NavLink click auto-closes. Backdrop `bg-black/40` added.
- **Logout** is a destructive ghost `Button` at the right edge of the slim topbar (icon-only `<sm:`, icon + label `sm:` up), positioned after the date + LocaleSwitch. The user-name block in the slim topbar is also a `DropdownMenu` trigger exposing Change Password (admin) + Logout.

**Why:** the user wanted a more compact desktop layout that reclaims the left 256 px for content, while keeping the option to flip back when they want the sidebar's verticality.

**How to apply:**
- Menu source-of-truth lives in [[frontend-nav-architecture]] at `frontend/src/lib/nav-sections.ts`. **Add new pages there**, not in Layout.tsx — both shells (Sidebar + TopNav) consume the same `SECTIONS` array via `filterAccessibleSections()`.
- Role gating still goes through `canAccessMenu()` from `auth.ts`. `superAdminOnly` / `adminOnly` / `menuKey` flags on `NavItem` are honored by `filterAccessibleSections()`.
- Hamburger behavior is viewport-derived at click time via `window.matchMedia('(min-width: 768px)')` — no resize listener. Keep it that way.
- If a future visual tweak needs sidebar-mode topbar to also offset for the TopNav strip, remember the conditional padding pattern: `pt-16` always + `md:pt-28` only when `showTopNav`.

Related: [[project-school-management-deployed]], [[feedback-spa-subpath-routing]], [[feedback-form-ux-patterns]].
