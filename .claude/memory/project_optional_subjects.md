---
name: project_optional_subjects
description: Principal's 2026-10-19 request — 11th/12th Mathematics is an additional subject taken by ~3 students; marks must count only for the students who take it (optional subjects + per-student enrolment).
metadata:
  type: project
---

**Request (principal, 2026-10-19, Punjabi voice note relayed by the user):** Nursery–10th setup is fine. In 11th and 12th (+1/+2), Mathematics is taken by only about three students, as an *additional* subject. Make it optional so its marks count only for those students; the rest must not show it as missing or have it in their totals.

**Data facts (TEST prod clone, 2026-10-19):** `class_subjects` has Mathematics (academic, 6 components, max 300) in both 11th and 12th; no Mathematics marks entered yet, so the takers can't be inferred — someone must tick them. 11th has 10 active students, 12th 13.

**Planned design:** `class_subjects.is_optional` + a per-student enrolment table; Marks Entry lists only enrolled students for an optional subject; the results engine gives non-takers a "not taken" subject that is left out of totals, max, completeness and pass/fail; report cards print it only for takers. Working rules (user relayed 2026-10-19: they stand until the principal says otherwise): a fail in an additional subject doesn't affect promotion; rank by percentage, not total, when subject sets differ; marks stay whole numbers (no 22.5).

**Still awaiting the principal (do NOT apply yet):** renaming the mistyped exam names in 11th/12th English ("PT First" → "P.T. First", "P.T Second" → "P.T. Second"), even on TEST. Until then a components-layout card for those classes prints them as separate columns.

**How to apply:** build after the Results cross-check is committed and on TEST; see [[project_results_policy]] for the confirmed rules it must keep.

**Status 2026-10-19 15:2x:** built and on TEST (commits 2ebe2e1 server / 585a5ed web / 32e1871 app, migration 0020; TEST app 1.3.1 build 22). On TEST, 11th and 12th Mathematics are optional with NO students ticked yet (the school ticks the real takers on Class Subjects → Mathematics). Not on prod.
