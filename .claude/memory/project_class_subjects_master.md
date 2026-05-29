---
name: project-class-subjects-master
description: Per-class subject roster + nested exam-component editor (super-admin), seeded from PDF (127 subjects / 654 components). Backs MarksEntry dropdowns and replaces free-text subject typing.
metadata:
  type: project
---

**Class Subjects master** shipped Session 13 (2026-05-24). Two-tier master managed by super-admin: `(class, subject)` rows with a `category` ENUM (`academic` | `co_curricular` | `grading`), and nested `(component_name, max_marks, order)` rows underneath each subject.

**Why:** marks were free-text subject names + free-text exam_type with no max_marks contract — teachers typoed columns into existence, max_marks defaulted to 100 globally regardless of subject, and there was no school-wide source of truth for what subjects each class actually offers.

**How to apply:**
- Super-admin opens **Academic → Class Subjects** at `/class-subjects` to manage. New deployments get the empty-state with a **"Seed KIS default pattern"** button → calls `POST /api/class-subjects/seed-defaults` → materialises 127 subjects + 654 components from [seed/exam_pattern.py](backend/app/seed/exam_pattern.py).
- Components per subject edited via the spreadsheet at `/class-subjects/:id` — atomic `PUT /api/class-subjects/{id}/components` replaces the whole list per save.
- MarksEntry binds: class dropdown → `GET /class-subjects?class=X` filtered to non-grading → subject pick → load detail → component dropdown (with `— max N` label) → max_marks auto-fills read-only.
- The seeded pattern is hand-derived from the school's handwritten PDF; values are ambiguous in spots (especially 9th–10th grand totals). Spot-check before relying on it.
- Related: [[project-marks-batches-workflow]], [[feedback-numberfield-clamp]].

Tables: `class_subjects`, `subject_exam_components`. Migration: `0008_class_subjects`.
