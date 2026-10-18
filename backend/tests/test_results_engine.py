"""Baseline behaviour of the pure results engine (app/services/results.py)."""
from types import SimpleNamespace as NS

import pytest

from app.services.results import aggregate_class_results, aggregate_student_subjects, grade_for


def comp(name, mx, term, order=0):
    return NS(component_name=name, max_marks=mx, term=term, order_index=order)


def subj(name, comps, category="academic", order=0, pa=None):
    return NS(subject_name=name, subject_name_pa=pa, category=category, order_index=order, components=comps)


def mark(sid, subject, exam_type, value):
    return NS(student_id=sid, subject=subject, exam_type=exam_type, marks=value)


MATHS = subj("Mathematics", [
    comp("P.T. First", 35, 1, 0),
    comp("P.T. Second", 35, 1, 1),
    comp("Semester First — Written", 70, 1, 2),
    comp("Semester First — Practical", 10, 1, 3),
    comp("P.T. Third", 35, 2, 4),
])
COMPUTER = subj("Computer", [comp("Term 1 Grade", 0, 1), comp("Term 2 Grade", 0, 2)], category="grading", order=10)


@pytest.mark.parametrize("marks,max_,grade", [
    (91, 100, "A1"), (90.9, 100, "A2"), (81, 100, "A2"), (71, 100, "B1"), (61, 100, "B2"),
    (51, 100, "C1"), (41, 100, "C2"), (40.9, 100, "D"), (0, 100, "D"), (5, 0, None),
])
def test_grade_bands(marks, max_, grade):
    assert grade_for(marks, max_) == grade


def test_scope_selects_components_by_term():
    for scope, expected_max in (("term1", 150), ("term2", 35), ("annual", 185)):
        res = aggregate_class_results(class_name="8th", session="2026-27", scope=scope,
                                      class_subjects=[MATHS], marks_rows=[], student_ids=[1])
        assert res.subject_columns[0].max == expected_max


def test_null_term_component_counts_in_both_terms():
    oral = subj("Hindi", [comp("Oral", 20, None), comp("P.T. First", 35, 1)])
    t1 = aggregate_class_results(class_name="8th", session="s", scope="term1", class_subjects=[oral],
                                 marks_rows=[], student_ids=[1])
    t2 = aggregate_class_results(class_name="8th", session="s", scope="term2", class_subjects=[oral],
                                 marks_rows=[], student_ids=[1])
    assert t1.subject_columns[0].max == 55
    assert t2.subject_columns[0].max == 20


def test_written_and_practical_sum_and_status():
    rows = [
        mark(1, "Mathematics", "P.T. First", 30),
        mark(1, "Mathematics", "Semester First — Written", 60),
        mark(1, "Mathematics", "Semester First — Practical", 9),
    ]
    res = aggregate_class_results(class_name="8th", session="s", scope="term1",
                                  class_subjects=[MATHS], marks_rows=rows, student_ids=[1, 2])
    s1, s2 = res.students
    assert s1.subjects[0].obtained == 99
    assert s1.subjects[0].status == "partial"          # P.T. Second not marked
    assert s1.subjects[0].components_marked == 3
    assert s2.subjects[0].status == "missing"
    assert s1.total_obtained == 99 and s1.total_max == 150
    assert s1.percentage == 66.0


def test_grading_subject_is_a_column_but_not_in_totals():
    rows = [mark(1, "Mathematics", "P.T. First", 35)]
    res = aggregate_class_results(class_name="8th", session="s", scope="term1",
                                  class_subjects=[MATHS, COMPUTER], marks_rows=rows, student_ids=[1])
    names = [c.subject_name for c in res.subject_columns]
    assert names == ["Mathematics", "Computer"]
    computer = res.students[0].subjects[1]
    assert computer.max == 0 and computer.percentage is None and computer.grade is None
    assert res.students[0].total_max == 150


def test_student_rollup_matches_class_rollup():
    rows = [mark(1, "Mathematics", "P.T. First", 20), mark(1, "Mathematics", "P.T. Third", 30)]
    cls = aggregate_class_results(class_name="8th", session="s", scope="annual",
                                  class_subjects=[MATHS], marks_rows=rows, student_ids=[1]).students[0]
    subjects, total, total_max, pct, grade = aggregate_student_subjects(
        scope="annual", class_subjects=[MATHS], marks_rows=rows)
    assert (total, total_max, pct, grade) == (cls.total_obtained, cls.total_max, cls.percentage, cls.grade)
    assert subjects[0].obtained == 50
