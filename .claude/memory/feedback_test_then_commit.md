---
name: feedback_test_then_commit
description: Owner's delivery flow — code → deploy to TEST → test (server checks + browser) → commit + push; prod only on an explicit go-ahead ("Not on prod"); share screenshots/samples for design sign-off.
metadata:
  type: feedback
---

Stated 2026-10-19: "after completing … code … then deploy, test it, then commit"; "Go test deployment, then code commit, not on prod".

**Why:** TEST is a prod clone the owner checks on their phone and in the browser before anything is final; prod changes reach every teacher (and app uploads force-update phones).

**How to apply:** deploy the working copy to TEST (Gotcha #23 pattern), run the `test-verification` skill, then commit in parts per area and push. Never deploy prod, release the prod APK or rename data without an explicit, current go-ahead — a "go ahead" for one list does not carry to later work. Send screenshots/sample PNGs (skill `sample-report-cards`) when design is involved; the owner relays principal decisions in Punjabi — confirm understanding briefly in English. Related: [[feedback_usage_pacing]], [[project_test_instance_on_prod_box]].
