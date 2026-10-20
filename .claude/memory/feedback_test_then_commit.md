---
name: feedback_test_then_commit
description: Owner's delivery flow — code → deploy TEST → test → commit + push; before go-live review the logs of the owner's own TEST run and fix regressions first; prod and app uploads only on an explicit current go-ahead; share screenshots for design sign-off.
metadata:
  type: feedback
---

Stated 2026-10-19: "after completing … code … then deploy, test it, then commit"; "Go test deployment, then code commit, not on prod".

**Why:** TEST is a prod clone the owner checks on their phone and in the browser before anything is final; prod changes reach every teacher (and app uploads force-update phones).

**How to apply:** deploy the working copy to TEST (Gotcha #23 pattern), run the `test-verification` skill, then commit in parts per area and push. Never deploy prod, release the prod APK or rename data without an explicit, current go-ahead — a "go ahead" for one list does not carry to later work. Send screenshots/sample PNGs (skill `sample-report-cards`) when design is involved; the owner relays principal decisions in Punjabi — confirm understanding briefly in English. Related: [[feedback_usage_pacing]], [[project_test_instance_on_prod_box]].

**Go-live routine (owner, 2026-10-20: "make it live, before that check test server logs … if anything need to fix"):** review TEST logs from their testing (skill `test-verification`, mode `review`), fix and re-verify any regression (it found one: Fees-menu staff refused `GET /fees`), then prod backup → `/deploy-prod-all` → `prod-smoke` → data steps → ask about app-upload timing (force update during school hours) — they chose "Upload now".
