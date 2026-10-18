"""Results engine v2: ranks, drafts, letter grades, per-exam columns, pass/promotion."""
from types import SimpleNamespace as NS

import pytest

from app.services.results import (
    aggregate_class_results, grade_legend, scope_from_term,
)


def comp(name, mx, term, order=0):
    return NS(component_name=name, max_marks=mx, term=term, order_index=order)


def subj(name, comps, category="academic", order=0, pa=None):
    return NS(subject_name=name, subject_name_pa=pa, category=category, order_index=order, components=comps)


def mark(sid, subject, exam_type, value=0, grade=None):
    return NS(student_id=sid, subject=subject, exam_type=exam_type, marks=value, grade=grade)


def full_term(name, order=0, category="academic"):
    """35 + 35 + (70 written + 10 practical) per term, like Maths in 6th-8th."""
    return subj(name, [
        comp("P.T. First", 35, 1, 0), comp("P.T. Second", 35, 1, 1),
        comp("Semester First — Written", 70, 1, 2), comp("Semester First — Practical", 10, 1, 3),
        comp("P.T. Third", 35, 2, 4), comp("P.T. Fourth", 35, 2, 5),
        comp("Semester Second — Written", 70, 2, 6), comp("Semester Second — Practical", 10, 2, 7),
    ], category=category, order=order)


def all_marks(sid, subject, pct):
    """Every component of full_term() at roughly `pct` percent."""
    out = []
    for name, mx in (("P.T. First", 35), ("P.T. Second", 35), ("Semester First — Written", 70),
                     ("Semester First — Practical", 10), ("P.T. Third", 35), ("P.T. Fourth", 35),
                     ("Semester Second — Written", 70), ("Semester Second — Practical", 10)):
        out.append(mark(sid, subject, name, round(mx * pct / 100)))
    return out


COMPUTER = subj("Computer", [comp("Term 1 Grade", 0, 1, 0), comp("Term 2 Grade", 0, 2, 1)], category="grading", order=10)


def run(scope, subjects, rows, ids, **kw):
    return aggregate_class_results(class_name="8th", session="2026-27", scope=scope,
                                   class_subjects=subjects, marks_rows=rows, student_ids=ids, **kw)


@pytest.mark.parametrize("term,scope", [
    ("Term I", "term1"), ("term 1", "term1"), ("Term II", "term2"), ("TERM 2", "term2"),
    ("Annual", "annual"), ("", "annual"), (None, "annual"), ("Half Yearly", None), ("Term-II 2025", None),
])
def test_scope_from_term_has_no_silent_fallback(term, scope):
    assert scope_from_term(term) == scope


def test_grade_legend_matches_bands():
    legend = grade_legend()
    assert legend[0] == {"grade": "A1", "range": "91–100"}
    assert legend[5] == {"grade": "C2", "range": "41–50"}
    assert legend[-1] == {"grade": "D", "range": "below 41"}


def test_competition_ranking_and_unranked_without_marks():
    maths = subj("Mathematics", [comp("P.T. First", 100, 1)])
    rows = [mark(1, "Mathematics", "P.T. First", 90), mark(2, "Mathematics", "P.T. First", 80),
            mark(3, "Mathematics", "P.T. First", 80), mark(4, "Mathematics", "P.T. First", 70)]
    res = run("term1", [maths], rows, [1, 2, 3, 4, 5])
    assert [s.rank for s in res.students] == [1, 2, 2, 4, None]
    assert res.ranked_count == 4 and res.class_size == 5


def test_drafts_flagged_and_optionally_left_out():
    maths = subj("Mathematics", [comp("P.T. First", 35, 1), comp("P.T. Second", 35, 1)])
    rows = [mark(1, "Mathematics", "P.T. First", 30), mark(1, "Mathematics", "P.T. Second", 20)]
    statuses = {("Mathematics", "P.T. First"): "submitted", ("Mathematics", "P.T. Second"): "draft"}
    incl = run("term1", [maths], rows, [1], batch_status_by_key=statuses)
    excl = run("term1", [maths], rows, [1], batch_status_by_key=statuses, include_drafts=False)
    assert incl.has_drafts and incl.subject_columns[0].batch_status == "draft"
    assert incl.students[0].total_obtained == 50
    assert excl.students[0].total_obtained == 30
    assert excl.students[0].draft_components == 1
    assert excl.students[0].subjects[0].status == "partial"
    assert not incl.complete


def test_letter_grades_per_scope():
    rows = [mark(1, "Computer", "Term 1 Grade", grade="a2"), mark(1, "Computer", "Term 2 Grade", grade="B1")]
    t1 = run("term1", [COMPUTER], rows, [1]).students[0].subjects[0]
    annual = run("annual", [COMPUTER], rows, [1]).students[0].subjects[0]
    assert t1.is_grading and t1.grade_letter == "A2" and t1.max == 0
    assert annual.grade_letter == "B1" and annual.term_letters == {1: "A2", 2: "B1"}
    bad = run("term1", [COMPUTER], [mark(1, "Computer", "Term 1 Grade", grade="Z")], [1]).students[0].subjects[0]
    assert bad.grade_letter is None and bad.status == "missing"


def test_term_columns_merge_written_and_practical():
    english = subj("English", [comp("P.T. First", 35, 1, 0), comp("P.T. Second", 35, 1, 1),
                               comp("Semester First", 80, 1, 2)], order=1)
    rows = [mark(1, "Mathematics", "Semester First — Written", 60),
            mark(1, "Mathematics", "Semester First — Practical", 9)]
    res = run("term1", [full_term("Mathematics"), english, COMPUTER], rows, [1])
    assert [g.key for g in res.groups] == ["P.T. First", "P.T. Second", "Semester First"]
    maths_cells = {c.key: c for c in res.students[0].subjects[0].cells}
    assert (maths_cells["Semester First"].obtained, maths_cells["Semester First"].max) == (69, 80)
    assert maths_cells["Semester First"].status == "complete"
    assert maths_cells["P.T. First"].status == "missing"
    assert res.students[0].subjects[2].cells == []          # grading subject has no numeric columns


def test_group_order_follows_school_exam_order_not_first_appearance():
    a = subj("Hindi", [comp("P.T. First", 35, 1, 0), comp("Semester First", 80, 1, 1)], order=0)
    b = subj("English", [comp("P.T. First", 35, 1, 0), comp("P.T. Second", 35, 1, 1),
                         comp("Semester First", 80, 1, 2)], order=1)
    assert [g.key for g in run("term1", [a, b], [], [1]).groups] == ["P.T. First", "P.T. Second", "Semester First"]


def test_annual_columns_are_terms():
    rows = all_marks(1, "Mathematics", 50)
    res = run("annual", [full_term("Mathematics")], rows, [1])
    assert [g.key for g in res.groups] == ["Term 1", "Term 2"]
    cells = res.students[0].subjects[0].cells
    assert [c.max for c in cells] == [150, 150]
    assert sum(c.obtained for c in cells) == res.students[0].subjects[0].obtained


@pytest.mark.parametrize("pcts,promotion", [
    ((60, 60, 60, 60), "Promoted"),
    ((20, 60, 60, 60), "Conditional"),
    ((20, 20, 60, 60), "Conditional"),
    ((20, 20, 20, 60), "Detained"),
])
def test_annual_promotion_rule(pcts, promotion):
    names = ["Hindi", "English", "Mathematics", "Science"]
    subjects = [full_term(n, order=i) for i, n in enumerate(names)]
    rows = [r for n, p in zip(names, pcts) for r in all_marks(1, n, p)]
    st = run("annual", subjects, rows, [1]).students[0]
    assert st.pass_status == ("pass" if promotion == "Promoted" else "fail")
    assert st.promotion == promotion


def test_incomplete_student_gets_no_promotion_and_term_scope_never_promotes():
    rows = all_marks(1, "Mathematics", 60)[:-1]          # last component not entered
    st = run("annual", [full_term("Mathematics")], rows, [1]).students[0]
    assert st.pass_status == "incomplete" and st.promotion is None
    assert run("term1", [full_term("Mathematics")], all_marks(1, "Mathematics", 60), [1]).students[0].promotion is None


def test_co_curricular_counts_in_total_but_not_in_pass():
    drawing = subj("Drawing", [comp("Term 1", 30, 1)], category="co_curricular", order=5)
    maths = subj("Mathematics", [comp("P.T. First", 100, 1)])
    rows = [mark(1, "Mathematics", "P.T. First", 60), mark(1, "Drawing", "Term 1", 3)]
    st = run("term1", [maths, drawing], rows, [1]).students[0]
    assert st.total_obtained == 63 and st.total_max == 130
    assert st.pass_status == "pass" and st.failed_subjects == []


def test_null_term_component_is_reported():
    oral = subj("Hindi", [comp("Oral", 20, None), comp("P.T. First", 35, 1)])
    res = run("term1", [oral], [], [1])
    assert any("Oral" in w for w in res.warnings)
