---
name: feedback-mysql-null-unique-upsert
description: MySQL treats NULL as distinct in UNIQUE indexes — combine a nullable FK with UNIQUE(parent_id, child_id) to get free upsert semantics on new rows while tolerating legacy NULL-parent rows. Used to ship marks_batches without backfilling.
metadata:
  type: feedback
---

When migrating an existing table to a new "batch-tracked" or "scope-tracked" parent, add the FK as **nullable** with `UNIQUE(parent_id, child_id)`. MySQL (unlike Postgres) treats NULL as *distinct* in unique indexes — so existing rows with `parent_id IS NULL` aren't constrained, but new rows (which always populate `parent_id`) hit the unique check and get free upsert semantics.

**Why:** Session 13 needed to ship the marks-batch workflow without touching 2 years of pre-existing marks rows (which already had duplicates from re-saves and no batch concept). Backfilling would have required dedup logic + a multi-stage migration. Instead `marks.batch_id BIGINT NULL` + `UNIQUE(batch_id, student_id)` gave us: (a) legacy rows unaffected, (b) new `POST /marks/batches` rows enforce one-per-student-per-batch automatically.

**How to apply:**
- Reusable for any "migrate to scoped X" feature: add scope-id column nullable, add UNIQUE(scope_id, child_id) — done. The new code always populates scope_id; the old code keeps writing NULL. Both coexist.
- **Postgres caveat:** Postgres treats NULL as equal-to-NULL only in some unique-index modes. This pattern relies on MySQL semantics. If the schema ever moves to Postgres, the unique constraint behavior must be rechecked.
- The legacy-row tolerance means GET endpoints need to handle both shapes (batch-aware and free-text). Currently `GET /marks` pivots both into MarksResults; `GET /marks/batches?...` only returns batch rows.
- Backfill is still a viable TODO (deduplicate by `(class, subject, exam_type, session, student_id)` keeping latest, then create one batch per quadruple). Tracked in CLAUDE.md Next Steps #4.
- Related: [[project-marks-batches-workflow]].
