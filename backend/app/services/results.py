"""Shared result aggregation: roll component-level marks up into per-subject
totals → grand total, scoped to Term 1 / Term 2 / Annual.

This is the single source of truth consumed by:
  - the on-screen results table  (GET /marks/results → aggregate_class_results)
  - the report-card PDF builder  (app/pdf/builder.py)

Pure functions, no DB access: routers fetch the rows, then call us.

Matching: a mark belongs to a component when `Marks.subject == subject_name`
and `Marks.exam_type == component_name`. A component's `term` (1 | 2 |
None = both terms) decides whether it is in the selected scope. Marks whose
exam_type is not a current component name don't match and are ignored.

Numeric components carry marks; components with max 0 belong to grading
subjects (Computer, P.E., …) and carry a letter grade in `Marks.grade`.

Policy knobs (assumptions the school can change in one place):
  - GRADE_BANDS: the A1…D bands used for computed grades, for the letters
    teachers pick on grading subjects, and for the legend printed on cards.
  - Rank: competition ranking ("1, 2, 2, 4") on total marks within the scope.
  - Pass: every academic subject at or above `pass_pct` (default 33 %).
  - Promotion (annual only): Promoted with no failed academic subject,
    Conditional with up to `conditional_max_fails`, Detained above that.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Scope = Literal["term1", "term2", "annual"]
SCOPES: tuple[str, ...] = ("term1", "term2", "annual")

# Bump when the computed numbers change meaning: the report-card cache hashes it.
RESULTS_ENGINE_VERSION = 2

# (letter, minimum percentage), best first.
GRADE_BANDS: tuple[tuple[str, float], ...] = (
    ("A1", 91), ("A2", 81), ("B1", 71), ("B2", 61), ("C1", 51), ("C2", 41), ("D", 0),
)
GRADE_LETTERS: tuple[str, ...] = tuple(letter for letter, _ in GRADE_BANDS)

PASS_PCT_DEFAULT = 33.0
CONDITIONAL_MAX_FAILS_DEFAULT = 2
PROMOTION_VALUES: tuple[str, ...] = ("Promoted", "Conditional", "Detained")

# Components named "Semester First — Written" / "Semester First — Practical"
# share the column "Semester First" on per-exam layouts.
GROUP_SEP = " — "

# Display order for the school's exam names; unknown names follow by position.
_KNOWN_GROUP_ORDER = (
    "P.T. First", "P.T. Second", "Semester First", "Oral I", "Term 1",
    "P.T. Third", "P.T. Fourth", "Semester Second", "Oral II", "Term 2", "Pre-Board",
)


# ── grades, terms, groups ───────────────────────────────────────────────
def grade_for(marks: float, max_marks: float) -> str | None:
    """KIS grade band for marks out of max; None when there is nothing to grade."""
    if max_marks <= 0:
        return None
    pct = (marks / max_marks) * 100
    for letter, min_pct in GRADE_BANDS:
        if pct >= min_pct:
            return letter
    return GRADE_BANDS[-1][0]


def grade_legend() -> list[dict[str, str]]:
    """[{grade: "A1", range: "91–100"}, …, {grade: "D", range: "below 41"}]."""
    out = []
    upper = 100
    for i, (letter, lo) in enumerate(GRADE_BANDS):
        if i == len(GRADE_BANDS) - 1:
            out.append({"grade": letter, "range": f"below {GRADE_BANDS[i - 1][1]:g}"})
        else:
            out.append({"grade": letter, "range": f"{lo:g}–{upper:g}"})
            upper = lo - 1
    return out


def normalize_grade_letter(value: Any) -> str | None:
    """'a1 ' → 'A1'; anything not in GRADE_LETTERS → None."""
    s = str(value or "").strip().upper()
    return s if s in GRADE_LETTERS else None


_TERM1 = {"term i", "term 1", "term-1", "term1", "t1", "1", "first", "first term", "1st term"}
_TERM2 = {"term ii", "term 2", "term-2", "term2", "t2", "2", "second", "second term", "2nd term"}
_ANNUAL = {"", "annual", "final", "full year", "year"}


def scope_from_term(term: str | None) -> Scope | None:
    """Map a template's term label to a scope; None when the label is not recognised.

    No silent fallback: an unrecognised label used to become "annual" and the
    card printed whole-year totals under a "Term II" heading.
    """
    t = " ".join((term or "").strip().lower().split())
    if t in _TERM1:
        return "term1"
    if t in _TERM2:
        return "term2"
    if t in _ANNUAL:
        return "annual"
    return None


def group_key(component_name: str) -> str:
    return component_name.split(GROUP_SEP, 1)[0].strip()


def _component_in_scope(term: int | None, scope: str) -> bool:
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
class ComponentInfo:
    component_name: str
    group: str
    term: int | None
    max: float


@dataclass
class ComponentMark:
    component_name: str
    group: str
    term: int | None
    max: float
    marks: float | None = None           # numeric components
    grade_letter: str | None = None      # grading components (max 0)
    batch_status: str | None = None      # "draft" | "submitted" | None (no batch)
    counted: bool = False                # contributed to totals / letters


@dataclass
class Cell:
    """One column of the per-exam layout for one subject: an exam group in a
    term scope ("P.T. First"), or a whole term ("Term 1") in the annual scope."""
    key: str
    obtained: float = 0.0
    max: float = 0.0
    marked: int = 0
    total: int = 0

    @property
    def status(self) -> str:
        if self.total == 0:
            return "none"           # subject has no component in this column
        if self.marked == self.total:
            return "complete"
        return "partial" if self.marked else "missing"


@dataclass
class SubjectColumn:
    subject_name: str
    subject_name_pa: str | None
    category: str
    order_index: int
    max: float                 # scope max = sum of in-scope component max_marks
    is_grading: bool = False
    batch_status: str = "none"     # submitted | draft | none (worst over in-scope components)
    components: list[ComponentInfo] = field(default_factory=list)


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
    is_grading: bool = False
    grade_letter: str | None = None            # grading subjects: letter for this scope
    term_letters: dict[int, str] = field(default_factory=dict)   # grading: {1: "A2", 2: "B1"}
    batch_status: str = "none"
    components: list[ComponentMark] = field(default_factory=list)
    cells: list[Cell] = field(default_factory=list)              # aligned with ClassResults.groups


@dataclass
class StudentResult:
    student_id: int
    subjects: list[SubjectResult]
    total_obtained: float
    total_max: float           # sum over graded subjects (max > 0) only
    percentage: float | None
    grade: str | None
    has_marks: bool = False
    rank: int | None = None
    pass_status: str | None = None          # pass | fail | incomplete | None (no marks)
    failed_subjects: list[str] = field(default_factory=list)
    promotion: str | None = None            # annual scope only
    draft_components: int = 0               # marks left out because their batch is a draft


@dataclass
class GroupColumn:
    key: str
    term: int | None
    order_index: int


@dataclass
class ClassResults:
    class_name: str
    session: str
    scope: str
    subject_columns: list[SubjectColumn]
    students: list[StudentResult]
    groups: list[GroupColumn] = field(default_factory=list)
    class_size: int = 0
    ranked_count: int = 0
    include_drafts: bool = True
    has_drafts: bool = False
    complete: bool = False          # every subject complete, nothing in draft: ranks are final
    engine_version: int = RESULTS_ENGINE_VERSION
    warnings: list[str] = field(default_factory=list)


# ── internal: per-subject scope plan (student-independent) ──────────────
@dataclass
class _Comp:
    name: str
    group: str
    term: int | None
    max: float
    position: int


@dataclass
class _SubjectScope:
    subject_name: str
    subject_name_pa: str | None
    category: str
    order_index: int
    components: list[_Comp]
    scope_max: float

    @property
    def is_grading(self) -> bool:
        return self.scope_max <= 0


def _subject_scopes(class_subjects: list[Any], scope: str) -> list[_SubjectScope]:
    """Per-subject in-scope component plan, ordered for display. Subjects with
    no components in the selected scope are dropped (no empty column)."""
    out: list[_SubjectScope] = []
    for cs in sorted(class_subjects, key=lambda s: (s.order_index, s.subject_name)):
        comps = [
            c for c in sorted(cs.components, key=lambda c: c.order_index)
            if _component_in_scope(c.term, scope)
        ]
        if not comps:
            continue
        plan = [
            _Comp(c.component_name, group_key(c.component_name), c.term, float(c.max_marks), i)
            for i, c in enumerate(comps)
        ]
        out.append(_SubjectScope(
            subject_name=cs.subject_name,
            subject_name_pa=cs.subject_name_pa,
            category=_cat(cs.category),
            order_index=cs.order_index,
            components=plan,
            scope_max=sum(c.max for c in plan),
        ))
    return out


def group_columns(plans: list[_SubjectScope], scope: str) -> list[GroupColumn]:
    """Column set for the per-exam layout. Term scopes: the exam groups used by
    numeric subjects. Annual: one column per term."""
    numeric = [p for p in plans if not p.is_grading]
    if scope == "annual":
        terms = sorted({c.term for p in numeric for c in p.components if c.term in (1, 2)})
        return [GroupColumn(f"Term {t}", t, i) for i, t in enumerate(terms)]
    seen: dict[str, tuple[int, int, int, int]] = {}
    appearance = 0
    for p in numeric:
        for c in p.components:
            known = _KNOWN_GROUP_ORDER.index(c.group) if c.group in _KNOWN_GROUP_ORDER else len(_KNOWN_GROUP_ORDER)
            key = (c.term or 3, known, c.position, appearance)
            if c.group not in seen or key < seen[c.group]:
                seen[c.group] = key
            appearance += 1
    ordered = sorted(seen.items(), key=lambda kv: kv[1])
    return [GroupColumn(g, k[0] if k[0] in (1, 2) else None, i) for i, (g, k) in enumerate(ordered)]


def _subject_batch_status(plan: _SubjectScope, batch_status_by_key: dict[tuple[str, str], str]) -> str:
    statuses = {batch_status_by_key.get((plan.subject_name, c.name)) for c in plan.components}
    if "draft" in statuses:
        return "draft"
    if "submitted" in statuses:
        return "submitted"
    return "none"


def _subject_result(
    plan: _SubjectScope,
    marks_by_component: dict[str, tuple[float, str | None]],
    *,
    scope: str,
    groups: list[GroupColumn],
    batch_status_by_key: dict[tuple[str, str], str],
    include_drafts: bool,
) -> tuple[SubjectResult, int]:
    """Roll one student's marks for one subject up to its scope total.
    Returns the result and how many marks were left out as drafts."""
    obtained = 0.0
    marked = 0
    excluded_drafts = 0
    comp_marks: list[ComponentMark] = []
    letters_by_term: dict[int, tuple[int, str]] = {}   # term -> (position, letter)
    for c in plan.components:
        status = batch_status_by_key.get((plan.subject_name, c.name))
        cm = ComponentMark(c.name, c.group, c.term, c.max, batch_status=status)
        entry = marks_by_component.get(c.name)
        if entry is not None:
            value, letter = entry
            if plan.is_grading:
                cm.grade_letter = normalize_grade_letter(letter)
            else:
                cm.marks = value
            usable = cm.grade_letter is not None if plan.is_grading else True
            if usable and (include_drafts or status != "draft"):
                cm.counted = True
                marked += 1
                if plan.is_grading:
                    t = c.term or 0
                    if t not in letters_by_term or c.position >= letters_by_term[t][0]:
                        letters_by_term[t] = (c.position, cm.grade_letter)
                else:
                    obtained += value
            elif usable:
                excluded_drafts += 1
        comp_marks.append(cm)

    total = len(plan.components)
    smax = plan.scope_max
    pct = (obtained / smax * 100.0) if smax > 0 else None
    status = "complete" if marked == total else ("partial" if marked > 0 else "missing")

    cells: list[Cell] = []
    if not plan.is_grading:
        for g in groups:
            cell = Cell(g.key)
            for c, cm in zip(plan.components, comp_marks):
                in_col = (c.term == g.term) if scope == "annual" else (c.group == g.key)
                if in_col:
                    cell.total += 1
                    cell.max += c.max
                    if cm.counted:
                        cell.marked += 1
                        cell.obtained += cm.marks or 0.0
            cells.append(cell)

    term_letters = {t: v[1] for t, v in letters_by_term.items() if t in (1, 2)}
    grade_letter = None
    if plan.is_grading and letters_by_term:
        # Annual shows the latest term's letter; a term scope has just one.
        grade_letter = letters_by_term[max(letters_by_term)][1]

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
        is_grading=plan.is_grading,
        grade_letter=grade_letter,
        term_letters=term_letters,
        batch_status=_subject_batch_status(plan, batch_status_by_key),
        components=comp_marks,
        cells=cells,
    ), excluded_drafts


def _group_marks(marks_rows: list[Any]) -> dict[int, dict[str, dict[str, tuple[float, str | None]]]]:
    """student_id -> subject -> {component_name: (marks, grade_letter)}."""
    out: dict[int, dict[str, dict[str, tuple[float, str | None]]]] = {}
    for m in marks_rows:
        out.setdefault(m.student_id, {}).setdefault(m.subject, {})[m.exam_type] = (
            float(m.marks or 0), getattr(m, "grade", None),
        )
    return out


def rank_students(students: list[StudentResult]) -> int:
    """Competition ranking on total marks among students who have marks.
    Sets `rank` in place and returns how many students were ranked."""
    ranked = [s for s in students if s.has_marks]
    totals = sorted((s.total_obtained for s in ranked), reverse=True)
    for s in ranked:
        s.rank = 1 + sum(1 for t in totals if t > s.total_obtained + 1e-9)
    return len(ranked)


def _pass_status(st: StudentResult, pass_pct: float) -> tuple[str | None, list[str]]:
    if not st.has_marks:
        return None, []
    academic = [s for s in st.subjects if s.category == "academic" and not s.is_grading]
    failed = [s.subject_name for s in academic
              if s.status == "complete" and (s.percentage or 0.0) < pass_pct]
    if any(s.status != "complete" for s in academic):
        return "incomplete", failed
    return ("fail" if failed else "pass"), failed


def promotion_for(
    st: StudentResult, *, conditional_max_fails: int = CONDITIONAL_MAX_FAILS_DEFAULT,
) -> str | None:
    """Promoted / Conditional / Detained from the annual pass status; None until complete."""
    if st.pass_status not in ("pass", "fail"):
        return None
    n = len(st.failed_subjects)
    if n == 0:
        return "Promoted"
    return "Conditional" if n <= conditional_max_fails else "Detained"


# ── public API ──────────────────────────────────────────────────────────
def aggregate_class_results(
    *,
    class_name: str,
    session: str,
    scope: str,
    class_subjects: list[Any],     # ClassSubject rows with .components loaded
    marks_rows: list[Any],         # Marks rows for (class_name, session)
    student_ids: list[int],        # roster order
    batch_status_by_key: dict[tuple[str, str], str] | None = None,   # (subject, component) -> status
    include_drafts: bool = True,
    pass_pct: float = PASS_PCT_DEFAULT,
    conditional_max_fails: int = CONDITIONAL_MAX_FAILS_DEFAULT,
) -> ClassResults:
    statuses = batch_status_by_key or {}
    plans = _subject_scopes(class_subjects, scope)
    groups = group_columns(plans, scope)
    columns = [
        SubjectColumn(
            p.subject_name, p.subject_name_pa, p.category, p.order_index, p.scope_max,
            is_grading=p.is_grading,
            batch_status=_subject_batch_status(p, statuses),
            components=[ComponentInfo(c.name, c.group, c.term, c.max) for c in p.components],
        )
        for p in plans
    ]
    grouped = _group_marks(marks_rows)

    students: list[StudentResult] = []
    for sid in student_ids:
        subj_marks = grouped.get(sid, {})
        subjects: list[SubjectResult] = []
        total_obtained = 0.0
        total_max = 0.0
        drafts_left_out = 0
        has_marks = False
        for p in plans:
            sr, excluded = _subject_result(
                p, subj_marks.get(p.subject_name, {}),
                scope=scope, groups=groups, batch_status_by_key=statuses, include_drafts=include_drafts,
            )
            drafts_left_out += excluded
            subjects.append(sr)
            if sr.max > 0:
                total_obtained += sr.obtained
                total_max += sr.max
                has_marks = has_marks or sr.components_marked > 0
        pct = (total_obtained / total_max * 100.0) if total_max > 0 else None
        st = StudentResult(
            student_id=sid,
            subjects=subjects,
            total_obtained=total_obtained,
            total_max=total_max,
            percentage=round(pct, 2) if pct is not None else None,
            grade=grade_for(total_obtained, total_max) if total_max > 0 else None,
            has_marks=has_marks,
            draft_components=drafts_left_out,
        )
        st.pass_status, st.failed_subjects = _pass_status(st, pass_pct)
        if scope == "annual":
            st.promotion = promotion_for(st, conditional_max_fails=conditional_max_fails)
        students.append(st)

    ranked = rank_students(students)
    has_drafts = any(c.batch_status == "draft" for c in columns)
    complete = bool(ranked) and not has_drafts and all(
        s.status == "complete" for st in students if st.has_marks for s in st.subjects
    )
    warnings = [
        f"{p.subject_name}: component {c.name!r} has no term, so it counts in both terms"
        for p in plans for c in p.components if c.term is None and c.max > 0
    ]
    return ClassResults(
        class_name=class_name, session=session, scope=scope,
        subject_columns=columns, students=students,
        groups=groups, class_size=len(student_ids), ranked_count=ranked,
        include_drafts=include_drafts, has_drafts=has_drafts, complete=complete,
        warnings=warnings,
    )


def aggregate_student_subjects(
    *,
    scope: str,
    class_subjects: list[Any],
    marks_rows: list[Any],         # already filtered to ONE student × class × session
    batch_status_by_key: dict[tuple[str, str], str] | None = None,
    include_drafts: bool = True,
) -> tuple[list[SubjectResult], float, float, float | None, str | None]:
    """Per-student roll-up. Returns (subjects, total_obtained, total_max, percentage, grade).
    Thin wrapper over aggregate_class_results so the two can never disagree."""
    sid = marks_rows[0].student_id if marks_rows else 0
    res = aggregate_class_results(
        class_name="", session="", scope=scope, class_subjects=class_subjects,
        marks_rows=marks_rows, student_ids=[sid],
        batch_status_by_key=batch_status_by_key, include_drafts=include_drafts,
    )
    st = res.students[0]
    return st.subjects, st.total_obtained, st.total_max, st.percentage, st.grade
