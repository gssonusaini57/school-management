# Session 12 — 2026-05-17 · Top-bar nav with hamburger toggle to sidebar mode

**Focus:** Replace the always-visible left sidebar (desktop default) with a horizontal top bar of section dropdowns. A hamburger toggle flips between top-bar and sidebar modes (preference persisted to `localStorage`). Mobile drawer behavior unchanged. Logout moved to slim topbar's right side (per user feedback).

**New files:**
- `frontend/src/lib/nav-sections.ts` — extracted hardcoded `SECTIONS` array + `NavItem`/`NavSection` types out of Layout.tsx; new `filterAccessibleSections(sections, user, isAdmin, isSuperAdmin)` helper reuses `canAccessMenu`. Both shells consume this so the menu source-of-truth lives in one place.
- `frontend/src/lib/nav-mode.ts` — `useNavMode()` hook returning `{ mode, setMode, toggle }`; persists `'topbar' | 'sidebar'` to `localStorage` key `kis.nav.mode` (default `topbar`). SSR-guarded.
- `frontend/src/components/ui/dropdown-menu.tsx` — standard shadcn Radix primitive.
- `frontend/src/components/Sidebar.tsx` — extracted dark left `<aside>` block. Props: `open`, `visibleOnDesktop`, `onItemClick`, `onChangePassword`, `onLogout`.
- `frontend/src/components/TopNav.tsx` — desktop-only horizontal nav. 5 dropdown triggers (Main / Academic / Administration / Stationery / Resources); section trigger turns `text-royal-gold` when any of its routes is active. Dark `bg-deep-indigo` band.

**Modified files:**
- `frontend/src/components/Layout.tsx` — slimmed to pure composition. Hamburger reads `window.matchMedia('(min-width: 768px)')` at click time: desktop toggles mode; mobile toggles drawer. Slim topbar always rendered; TopNav only when `mode === 'topbar'`. User name in slim topbar is a DropdownMenu (Change Password + Logout); standalone Logout button at the right.

**Decisions:** section dropdowns; persist mode in `localStorage` `kis.nav.mode` (default `topbar`); mobile ignores the value; slim topbar in both modes.

**Deploys:** Two `/deploy-test-frontend`. Bundle 925 KB JS / 284 KB gz. Plan file: `~/.claude/plans/so-i-want-a-linked-popcorn.md`.
