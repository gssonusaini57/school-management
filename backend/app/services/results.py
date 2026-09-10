"""Shared result aggregation: roll component-level marks up into per-subject
totals → grand total, scoped to Term 1 / Term 2 / Annual.

This is the single source of truth consumed by BOTH:
  - the on-screen results table  (GET /marks/results → aggregate_class_results)
  - the report-card PDF builder  (build_report_card_payload → aggregate_student_subjects)

Pure functions, no DB access — routers fetch the rows then call us (mirrors
app/pdf/builder.py's convention).

Marks are matched to a subject's components by `Marks.exam_type == component_name`
and `Marks.subject == subject_name`. A component's `term` (1 | 2 | None=both)
decides whether it's in the selected scope. Legacy marks whose exam_type is not
a current component name simply don't match and are ignored.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


Scope = Literal["term1", "term2", "annual"]


# ── grade band (single source — builder.py imports grade_for from here) ──
def grade_for(marks: float, max_marks: float) -> str | None:
    """KIS grade band; returns None when there's nothing to grade (max <= 0)."""
    if max_marks <= 0:
        return None
    pct = (marks / max_marks) * 100
    if pct >= 91: return "A1"
    if pct >= 81: return "A2"
    if pct >= 71: return "B1"
    if pct >= 61: return "B2"
    if pct >= 51: return "C1"
    if pct >= 41: return "C2"
    return "D"


def scope_from_term(term: str | None) -> Scope:
    """Map a template's free-text term ("Term I"/"Term II"/"Annual"/None) to a scope."""
    t = (term or "").strip().lower()
    if t in ("term i", "term 1", "term-1", "t1", "1", "first"):
        return "term1"
    if t in ("term ii", "term 2", "term-2", "t2", "2", "second"):
        return "term2"
    return "annual"


def _component_in_scope(term: int | None, scope: Scope) -> bool:
    # NULL term = applies to BOTH terms (counts in every scope).
    if scope == "annual":
        return True
    want = 1 if scope == "term1" else 2
    return term is None or term == want


def _cat(category: Any) -> str:
    """SubjectCategory enum (or already a str) → its string value."""
    return getattr(category, "value", category)


# ── public return shapes ────────────────────────────────────────────────
@dataclass
class SubjectColumn:
    subject_name: str
    subject_name_pa: str | None
    category: str
    order_index: int
    max: float                 # scope max = sum of in-scope component max_marks


@dataclass
class SubjectResult:
    subject_name: str
    subject_name_pa: str | None
    category: str
    order_index: int
    obtained: float
    max: float
    percentage: float | None   # None when max == 0 (grading subjects)
    grade: str | None
    components_total: int
    components_marked: int
    status: str                # "complete" | "partial" | "missing"


@dataclass
class StudentResult:
    student_id: int
    subjects: list[SubjectResult]
    total_obtained: float
    total_max: float           # sum over graded subjects (max > 0) only
    percentage: float | None
    grade: str | None


@dataclass
class ClassResults:
    class_name: str
    session: str
    scope: str
    subject_columns: list[SubjectColumn]
    students: list[StudentResult]


# ── internal: per-subject scope plan (student-independent) ──────────────
@dataclass
class _SubjectScope:
    subject_name: str
    subject_name_pa: str | None
    category: str
    order_index: int
    components: list[tuple[str, float]]   # (component_name, max_marks) in scope
    scope_max: float


def _subject_scopes(class_subjects: list[Any], scope: Scope) -> list[_SubjectScope]:
    """Per-subject in-scope component plan, ordered for display. Subjects with
    no components in the selected scope are dropped (no empty column)."""
    out: list[_SubjectScope] = []
    for cs in sorted(class_subjects, key=lambda s: (s.order_index, s.subject_name)):
        comps = [
            (c.component_name, float(c.max_marks))
            for c in sorted(cs.components, key=lambda c: c.order_index)
            if _component_in_scope(c.term, scope)
        ]
        if not comps:
            continue
        out.append(_SubjectScope(
            subject_name=cs.subject_name,
            subject_name_pa=cs.subject_name_pa,
            category=_cat(cs.category),
            order_index=cs.order_index,
            components=comps,
            scope_max=sum(m for _, m in comps),
        ))
    return out


def _subject_result(plan: _SubjectScope, marks_by_component: dict[str, float]) -> SubjectResult:
    obtained = 0.0
    marked = 0
    for comp_name, _comp_max in plan.components:
        if comp_name in marks_by_component:
            obtained += marks_by_component[comp_name]
            marked += 1
    total = len(plan.components)
    smax = plan.scope_max
    pct = (obtained / smax * 100.0) if smax > 0 else None
    status = "complete" if marked == total else ("partial" if marked > 0 else "missing")
    return SubjectResult(
        subject_name=plan.subject_name,
        subject_name_pa=plan.subject_name_pa,
        category=plan.category,
        order_index=plan.order_index,
        obtained=obtained,
        max=smax,
        percentage=round(pct, 2) if pct is not None else None,
        grade=grade_for(obtained, smax) if smax > 0 else None,
        components_total=total,
        components_marked=marked,
        status=status,
    )


def _group_by_subject_component(marks_rows: list[Any]) -> dict[str, dict[str, dict[str, float]]]:
    """student_id -> subject -> {component_name: marks}."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    for m in marks_rows:
        out.setdefault(m.student_id, {}).setdefault(m.subject, {})[m.exam_type] = float(m.marks)
    return out


# ── public API ──────────────────────────────────────────────────────────
def aggregate_class_results(
    *,
    class_name: str,
    session: str,
    scope: Scope,
    class_subjects: list[Any],     # ClassSubject rows with .components loaded
    marks_rows: list[Any],         # Marks rows for (class_name, session)
    student_ids: list[int],        # roster order
) -> ClassResults:
    plans = _subject_scopes(class_subjects, scope)
    columns = [
        SubjectColumn(p.subject_name, p.subject_name_pa, p.category, p.order_index, p.scope_max)
        for p in plans
    ]
    grouped = _group_by_subject_component(marks_rows)

    students: list[StudentResult] = []
    for sid in student_ids:
        subj_marks = grouped.get(sid, {})
        subjects: list[SubjectResult] = []
        total_obtained = 0.0
        total_max = 0.0
        for p in plans:
            sr = _subject_result(p, subj_marks.get(p.subject_name, {}))
            subjects.append(sr)
            if sr.max > 0:
                total_obtained += sr.obtained
                total_max += sr.max
        pct = (total_obtained / total_max * 100.0) if total_max > 0 else None
        students.append(StudentResult(
            student_id=sid,
            subjects=subjects,
            total_obtained=total_obtained,
            total_max=total_max,
            percentage=round(pct, 2) if pct is not None else None,
            grade=grade_for(total_obtained, total_max) if total_max > 0 else None,
        ))

    return ClassResults(
        class_name=class_name, session=session, scope=scope,
        subject_columns=columns, students=students,
    )


def aggregate_student_subjects(
    *,
    scope: Scope,
    class_subjects: list[Any],
    marks_rows: list[Any],         # already filtered to ONE student × class × session
) -> tuple[list[SubjectResult], float, float, float | None, str | None]:
    """Per-student roll-up for the report-card builder. Returns
    (subjects, total_obtained, total_max, percentage, grade)."""
    plans = _subject_scopes(class_subjects, scope)
    subj_marks: dict[str, dict[str, float]] = {}
    for m in marks_rows:
        subj_marks.setdefault(m.subject, {})[m.exam_type] = float(m.marks)

    subjects: list[SubjectResult] = []
    total_obtained = 0.0
    total_max = 0.0
    for p in plans:
        sr = _subject_result(p, subj_marks.get(p.subject_name, {}))
        subjects.append(sr)
        if sr.max > 0:
            total_obtained += sr.obtained
            total_max += sr.max
    pct = round(total_obtained / total_max * 100.0, 2) if total_max > 0 else None
    grade = grade_for(total_obtained, total_max) if total_max > 0 else None
    return subjects, total_obtained, total_max, pct, grade
