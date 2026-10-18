---
name: feedback_cache_key_all_inputs
description: A derived-artifact cache must key on EVERY table it reads, not just the one with a version column. pdf_cache keyed only on template_version and served stale report cards after a marks edit; fixed with a source_hash of the marks + student data.
metadata:
  type: feedback
---

Before caching a derived artifact, enumerate every table it is rendered from and make sure each one is either **in the cache key** or **hashed into it**. A version column on one input is not a cache key for all of them.

**Why:** `pdf_cache` was keyed `(kind, student_id, template_id, template_version)`. That covered template edits — `PATCH /pdf/templates/{id}` bumps `version`, which invalidates. But a report card is also rendered from the `marks` table and `pdf_student_data`, and editing *those* bumps nothing. So the sequence "render card → teacher corrects a mark → re-render" served the stale PDF, with no error and no sign anything was wrong. A wrong report card handed to a parent is about the worst failure mode this app has.

**How to apply:**
- Fix shipped in Session 18 (migration 0013): `pdf_cache.source_hash` = sha1 over the sorted `subject|exam_type|marks|max_marks` tuples plus the sort-keyed JSON of the per-student data. The lookup matches `source_hash` alongside `template_version`, so any edit to either input misses and re-renders.
- The structural consequence is worth knowing before you copy the pattern: `render_or_cache` must **gather its render inputs BEFORE the cache lookup**, because the hash needs them. That inverts the natural "check the cache first, load nothing on a hit" ordering — a hit now costs two extra cheap SELECTs. Acceptable here; measure it before reusing on a hot path.
- Pre-existing rows get `source_hash IS NULL` and the lookup treats NULL as its own key, so they miss exactly once and then store the hash. No backfill needed.
- Related: [[project_results_aggregation]], [[project_pdf_templates_flow]], [[feedback_auto_cache_bust]] (the same staleness class, one layer up — browser cache vs server cache).
