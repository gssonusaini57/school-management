---
name: reference-plan-file
description: Plan-mode files for this project. The path rotates per request (Claude generates a new slug each plan-mode invocation), so check `/Users/manjeetsaini/.claude/plans/` for the newest mtime when in doubt.
metadata:
  type: reference
---

Plan-mode files for school-management live under `/Users/manjeetsaini/.claude/plans/`. The path **rotates** — Claude generates a fresh slug per plan-mode session, so there's not one canonical filename. Known plan files used so far:

- `reactive-chasing-crab.md` — Session 4 (deploy framework), Session 8 early (KIS design retrofit), Session 8 late (templated PDF flow). Overwritten three times.
- `so-i-want-a-linked-popcorn.md` — Session 12 (top-bar nav).
- `add-draft-functionaly-to-merry-popcorn.md` — Session 13 (marks draft/lock workflow).

**How to apply:** When the user re-enters plan mode, the harness assigns a fresh path. Check the system reminder for the current filename. To find the newest plan: `ls -t /Users/manjeetsaini/.claude/plans/*.md | head -1`.

When editing a plan during plan mode: only the plan file is writable; the harness rejects edits to anything else. Use `Write` (the plan starts empty) or `Edit` (when iterating).
