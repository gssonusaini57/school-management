---
name: project_results_aggregation
description: One shared engine (app/services/results.py) rolls per-component marks up to per-subject totals scoped to Term 1 / Term 2 / Annual; feeds both GET /marks/results and the report-card PDF. Migration 0013 adds component.term + pdf_cache.source_hash.
metadata:
  type: project
---

**Term-scoped result aggregation** — Session 18 (2026-10-18), now commit `014c069` after the history rewrite. **Live on prod** since the 2026-06-07 deploy (prod schema 0013, verified 2026-10-19).

**Status 2026-10-19:** v2 is complete and on TEST (schema 0021, Sessions 18–19): academic sessions, letter grades, rank/attendance, report card v2 with layouts and photo, background renders + ZIP, batch revision guard (0018), v1 overrides cleared (0019), optional subjects (0020, `not_taken`). v2 went live on prod on 2026-10-20 (schema 0021). The v1 notes below are historical: drafts are now flagged on screen and left off cards. Detail: `.claude/SESSION_HISTORY_19.md`; rules: [[project_results_policy]], [[project_optional_subjects]].

Marks are entered per exam *component* (`marks.exam_type` holds a `component_name` like "Semester Second — Practical"), but there was no notion of which term a component belonged to, so nothing could produce a Term-1 or Term-2 total. The results screen also filtered on a hardcoded free-text exam list unrelated to the class-subjects master, and the report-card PDF did its own flat per-subject sum with its own private grade function.

**Why one engine:** the screen and the printed card were two independent implementations of "what did this student score". [backend/app/services/results.py](backend/app/services/results.py) is now the only one — pure functions, no DB access (routers fetch rows and pass them in, mirroring `app/pdf/builder.py`'s convention). `grade_for` moved there out of `builder.py`.

**How to apply:**
- `subject_exam_components.term` is `1` | `2` | `NULL`, where **NULL means "counts in both terms"** — so a NULL on a graded component silently inflates both term totals. Migration 0013 backfills it by `LIKE` on the seeded KIS component-name patterns; hand-renamed components land NULL and need a manual fix via the new Term column on `/class-subjects/:id`.
- `GET /api/marks/results?class=&session=&scope=term1|term2|annual` returns `{subject_columns, students[]}` with students joined server-side. It **includes draft marks** (no batch-status filter) — a teacher cannot tell submitted from draft yet. Legacy marks whose `exam_type` isn't a current component name match nothing and are silently ignored.
- `scope_from_term()` maps a PDF template's free-text `term` ("Term I" / "Term 2" / "Annual" / None) onto the scope enum; the report card renders only graded subjects (`max > 0`), with grading-category subjects coming from the co-scholastic block in `pdf_student_data` instead.
- Migration 0013 also widens `marks.exam_type` 60→80 (it stores a `component_name`, already VARCHAR(80)) and adds `pdf_cache.source_hash` — see [[feedback_cache_key_all_inputs]].
- Related: [[project_class_subjects_master]], [[project_marks_batches_workflow]], [[project_pdf_templates_flow]].

Tables touched: `subject_exam_components` (+`term`), `marks` (widened), `pdf_cache` (+`source_hash`). Migration: `0013_component_term`.
