# Session History — Sessions 1–2 (Firebase Era, Pre-Migration)

These sessions describe the **original Firebase Firestore + Storage** implementation, which was fully replaced in Session 3 (FastAPI + MySQL migration). The old single-file `index.html` is preserved at [_archive/index.firebase.html](../_archive/index.firebase.html) for reference but is no longer wired up.

---

## Session 2 — 2026-05-07 (early/morning)
**Focus:** Upload system overhaul + recurring admin login fix + Firebase rules

**Changes made:**
- `3d043e9` — Background upload sync: form closes immediately after Firestore save; files upload async with floating badge
- `870b5e9` — Parallel multi-file uploads via `Promise.all`; client-side image compression (900px/0.75 JPEG)
- `bcab824` — Isolate Firestore password check in nested try-catch so network errors fall back to `admin123`
- `7f96d79` — Upload badge: live % progress bar, green success state, red retry hint on failure
- `d9dc23e` — No-cache meta headers to stop GitHub Pages serving stale versions
- `storage.rules` updated locally to `allow read, write: if true` (NEVER deployed by user — caused recurring "Missing or insufficient permissions" until migration)
- Diagnosed "Missing or insufficient permissions" — cause was Firestore/Storage rules not deployed in Firebase Console (NOT a JS auth issue — app uses no Firebase Auth)

**Key insight:** User repeatedly reported "admin can't open" after each push. Root cause was always GitHub Pages CDN caching, not code bugs. The recurring rules-deploy friction was a major motivation for moving off Firebase.

---

## Session 1 — 2026-05-05 to 2026-05-06
**Focus:** Core portal build + login fixes + multi-class staff + change password

**Changes made:**
- `f15743d` — Login form: Admin/Staff field toggle
- `ce20d33` — Fix `window.toggleAuthFields()` call inside ES module scope
- `d8fb032` — Remove undeclared `handleEditUploadPreview` from `Object.assign` (crashed entire module)
- `263ebbb` — Multi-class staff assignment: checkbox grid, `assignedClasses[]` array in Firestore
- `1feb435` — Admin Change Password: stored in `settings/admin_auth`, syncs across devices

**Stack at the time:** Single `index.html` (~2300 lines) talking directly to Firebase Firestore 10.8.0 + Firebase Storage 10.8.0 over CDN ES modules. Hosted on GitHub Pages. No backend. Auth was app-level (admin password in `settings/admin_auth` doc, staff `accessCode` in `staff_roles` collection). Real-time updates via 8 `onSnapshot` listeners.

**Why this stack was abandoned (Session 3):**
1. Open Firestore/Storage rules (`allow read, write: if true`) and rules-deploy operational pain.
2. Plaintext admin password.
3. No real auth — anyone with the API key could read/write.
4. Real-time listener tight-coupling to Firestore APIs.
5. Vendor lock-in.
