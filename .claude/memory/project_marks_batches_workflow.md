---
name: project-marks-batches-workflow
description: Marks Entry draft → submit → lock → edit-request workflow. New marks_batches + marks_edit_requests tables. Mirror of student-edit-request pattern.
metadata:
  type: project
---

**Marks draft/lock workflow** shipped Session 13 (2026-05-24). Replaces the append-only-INSERT-into-marks pattern (which silently duplicated rows on re-save) with a batch-tracked, lockable workflow that mirrors the existing `student_edit_requests` pattern from Session 9.

**Why:** teachers re-saved the same exam batch and the system happily created duplicate rows. No concept of "finalised", no audit trail for submission, no ability to lock marks once the exam was tallied.

**How to apply:**
- New table `marks_batches` keyed on UNIQUE `(class_name, subject, exam_type, session)` with `status ∈ {draft, submitted}`. Marks rows get nullable `batch_id` FK plus UNIQUE `(batch_id, student_id)` (MySQL treats NULL as distinct so legacy rows skip the constraint — see [[feedback-mysql-null-unique-upsert]]).
- New table `marks_edit_requests` (mirror of `student_edit_requests`) with required `reason TEXT NOT NULL`. Status flow: `pending → approved | rejected`. Approve flips batch back to `draft` indefinitely (no timer; teacher re-submits manually).
- API: `GET/POST /api/marks/batches`, `POST /{id}/submit`, `POST /{id}/request-edit`, super-admin queue `GET/POST /api/admin/marks-edit-requests/*`. Legacy `POST /api/marks/bulk` + `bulk-import` stay for CSV imports (write `batch_id IS NULL`).
- Frontend: 3-state MarksEntry (New/Draft → Submitted+locked → Submitted+pending-request). Super-admin always bypasses the lock and edits directly — they don't request from themselves. Tabbed `/edit-requests` page with auto-switch to whichever queue has pending items.
- Bulk-import path is unchanged — admins can keep doing CSV migrations of historical marks without going through the lock workflow.
- Related: [[project-class-subjects-master]] (provides the dropdown source), [[feedback-numberfield-clamp]] (per-student input).

Tables: `marks_batches`, `marks_edit_requests` + `marks.batch_id` FK. Migration: `0009_marks_batches_edit_requests`.
