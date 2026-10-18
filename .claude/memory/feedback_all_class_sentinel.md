---
name: feedback_all_class_sentinel
description: Staff assigned every class are stored as ONE staff_classes row with the literal "All"; that sentinel must be expanded to concrete class names at the auth boundary (login AND token decode), or clients render a bogus "All" and assert_class_allowed rejects real classes.
metadata:
  type: feedback
---

A sentinel value that stands for "all of them" must be expanded at the boundary where it leaves storage — not passed through to clients and re-interpreted by each one.

**Why:** `staff_classes` stores "this teacher has every class" as a single row with `class_name = "All"` (the staff bulk-import writes it; the web multi-select collapses a full selection back to `["All"]`). That literal flowed straight into the JWT `allowed_classes` claim and out through `GET /api/auth/me`. Two failures followed: the Android app and the web class pickers rendered a bogus "All" entry alongside the real classes, and `assert_class_allowed` compared a real class name against `["All"]` and returned 403 — so the staff with the *broadest* access were the ones locked out. Fixed Session 18, commit `03907d8`.

**How to apply:**
- [backend/app/constants.py](backend/app/constants.py) owns the canonical ordered `CLASSES` list plus `expand_classes()` / `is_all_sentinel()`. That list is duplicated in `frontend/src/lib/utils.ts` and in the Android app — **three copies, keep them in sync** when a class is added.
- Expansion runs in **two** places deliberately: in `routers/auth.py` before the token is minted, and again in `deps._parse` on every decode. The second is not redundant — it is what repairs tokens that were already issued before the fix and stay valid for up to 8h. Any time you fix the *content* of a long-lived token claim, fix it on the read path too or wait out the TTL.
- `assert_class_allowed` also short-circuits on the sentinel as a belt-and-braces guard for anything still carrying it.
- New clients that read `allowed_classes` receive concrete names. Do not special-case the string `"All"` again on the client.
