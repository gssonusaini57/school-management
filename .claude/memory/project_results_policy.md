---
name: project_results_policy
description: Results/report-card policy the principal confirmed on 2026-10-19 (terms, ties, half day, pass/promotion, grade letters) — treat as settled, don't re-ask.
metadata:
  type: project
---

The KIS principal confirmed these results-module defaults on **2026-10-19** (relayed by the user; "everything else is fine"):

- Term 1 = April–September, Term 2 = October–March (session April–March, e.g. "2026-27").
- Tied students share a rank (competition ranking 1, 2, 2, 4).
- A half day (attendance `H`) counts as 0.5 days present; holidays don't count as working days.
- Pass mark 33 % per academic subject; annual result Promoted (0 fails) / Conditional (≤ 2 fails) / Detained (> 2).
- Graded subjects (Computer, E.V.S., …) use letters A1–D.
- Punjabi UI/PDF labels were drafted by an agent; the principal didn't object, but a native proofread is still welcome.

**Why:** these were open "confirm with the principal" defaults in the Results plan (`~/.claude/plans/sharded-brewing-cocoa.md`, decisions A1–A6); the code already uses exactly these values (engine constants, `academic_sessions` defaults, template `promotionRule` = null → school default).

**How to apply:** don't re-raise them as questions; only change them if the school asks. Still open after this confirmation: optional subjects ([[project_optional_subjects]]), whether half marks are ever given (marks are whole numbers today), and the rank basis when students' subject sets differ.
