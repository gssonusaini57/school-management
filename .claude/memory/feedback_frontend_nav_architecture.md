---
name: frontend-nav-architecture
description: Admin-portal menu structure is a single shared registry consumed by both Sidebar and TopNav; never hardcode nav items inside Layout.tsx.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b9349413-a203-442a-ad69-8a0001e39e16
---

Don't hardcode nav items, sections, icons, or role gating inside `frontend/src/components/Layout.tsx`. The admin-portal menu has two shells (top bar in `'topbar'` mode, left aside in `'sidebar'` mode + mobile drawer) and they must stay in sync.

**Why:** Before Session 12, Layout.tsx owned the `SECTIONS` array (~40 lines hardcoded with icons + `adminOnly`/`superAdminOnly`/`menuKey` flags). Adding a new page meant editing Layout. With two shells now, duplication would drift instantly.

**How to apply:**
- Add new menu items to `frontend/src/lib/nav-sections.ts` — append to the appropriate section in `SECTIONS`. The shape is `{ to, labelKey, icon, menuKey? | adminOnly? | superAdminOnly? }`.
- If the page is staff-grantable (super-admin can tick it per-staff), use `menuKey` and also add the key to `MenuKey` union in `frontend/src/lib/menus.ts` + the backend `permissions.py`. Otherwise use `adminOnly`/`superAdminOnly`.
- Both `Sidebar.tsx` and `TopNav.tsx` import `SECTIONS` + `filterAccessibleSections()` — no edits needed to either shell when adding/removing items.
- i18n keys go under `portal.nav.*` in both `packages/design-system/i18n/portal-{en,pa}.json`.
- New section? Add `titleKey` to `SECTIONS`, plus the `portal.nav.section<Name>` key in both i18n files.

Related: [[project-topbar-nav-redesign]].
