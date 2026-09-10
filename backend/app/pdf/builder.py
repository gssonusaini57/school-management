"""Build the full validated render payload for a (kind, student) pair.

Inputs:
  - PdfTemplate row (class-level config; `data` JSON validated by the
    matching *TemplateData schema before persistence so we trust its shape).
  - Student row (DB record).
  - PdfStudentData row | None (per-student overrides; may be missing).
  - For report-card: a list of Marks rows for this student × class × exam_type.

Output: a validated `ReportCard` or `PsebAdmitCard` Pydantic model. The
caller hands `model_dump(by_alias=True, mode="json")` to render_pdf.

Pure functions; no DB access here. Routers fetch the rows then call us.
"""
from __future__ import annotations

from datetime import date as DateT
from typing import Any

from .schemas import (
    Bilingual,
    PsebAdmitCard, PsebCandidate,
    ReportCard, ReportCardStudent, ReportCardSubject, ReportCardSummary,
    ReportCardSignatures,
)
from ..services.results import aggregate_student_subjects, Scope


def _bi(s: str | None) -> Bilingual:
    """Wrap a single string as a Bilingual{en,pa}, both filled with the
    same text. Used when the underlying Student row only has one column
    and we need a Bilingual on the print template."""
    text = s or "—"
    return Bilingual(en=text, pa=text)


def build_report_card_payload(
    *,
    template_data: dict[str, Any],
    student: Any,                      # app.models.student.Student
    student_data: dict[str, Any] | None,
    session: str,
    term: str | None,
    scope: Scope,
    class_subjects: list[Any],         # app.models.class_subject.ClassSubject (+components)
    marks_rows: list[Any],             # app.models.marks.Marks (this student × class × session)
) -> ReportCard:
    """Merge a template + student + per-student data + component-aggregated
    marks into a fully-validated ReportCard model. Marks are rolled up to one
    row per subject (sum of in-scope components) by the shared results engine."""
    sd = student_data or {}

    subj_results, total, max_total, pct_opt, _grade = aggregate_student_subjects(
        scope=scope, class_subjects=class_subjects, marks_rows=marks_rows,
    )
    # Scholastic table = graded subjects only (max > 0); grading subjects are
    # rendered from the co-scholastic block (pdf_student_data), not from marks.
    subjects = [
        ReportCardSubject(
            name=Bilingual(en=sr.subject_name, pa=sr.subject_name_pa or sr.subject_name),
            marks=sr.obtained,
            max=sr.max,
            grade=sr.grade,
        )
        for sr in subj_results
        if sr.max > 0
    ]
    pct = pct_opt or 0.0

    co_scholastic = []
    head_lookup = {h["name"]["en"]: h["name"] for h in template_data.get("coScholasticHeads", [])}
    for entry in sd.get("coScholasticGrades", []) or []:
        name_obj = head_lookup.get(entry["head"], {"en": entry["head"], "pa": entry["head"]})
        co_scholastic.append({
            "name": name_obj.get("en", entry["head"]),
            "grade": entry["grade"],
        })

    sigs_in = template_data.get("signatures") or {}
    signatures = ReportCardSignatures(
        classTeacher=sigs_in.get("classTeacher"),
        examIncharge=sigs_in.get("examIncharge"),
        principal=sigs_in.get("principal"),
    )

    summary = ReportCardSummary(
        total=total,
        max=max_total,
        percentage=round(pct, 2),
        rank=sd.get("rank"),
        classSize=sd.get("classSize"),
        attendancePct=sd.get("attendancePct"),
        workingDays=sd.get("workingDays"),
        daysPresent=sd.get("daysPresent"),
        remarks=Bilingual(**sd["remarks"]) if sd.get("remarks") else None,
        promotion=sd.get("promotion") or template_data.get("promotionDefault") or (
            "Promoted" if pct >= 33 else "Needs improvement"
        ),
    )

    student_block = ReportCardStudent(
        name=_bi(student.name),
        **{"class": student.class_name},
        section="—",
        rollNo=(student.roll_no or str(student.id)),
        fatherName=_bi(student.father),
        motherName=_bi(student.mother),
        dob=student.dob or DateT(2010, 1, 1),
        house=sd.get("house"),
        admissionNo=sd.get("admissionNo") or student.admission_id,
        photoUrl=None,
    )

    display_term = term or ("Annual" if scope == "annual" else None)
    return ReportCard(
        session=session,
        term=display_term,
        student=student_block,
        subjects=subjects,
        coScholastic=co_scholastic,
        summary=summary,
        signatures=signatures,
    )


def build_pseb_admit_payload(
    *,
    template_data: dict[str, Any],
    student: Any,
    student_data: dict[str, Any],
    session: str,
) -> PsebAdmitCard:
    """Merge the PSEB admit-card template + student + per-student PSEB-specific
    fields into a validated PsebAdmitCard model."""
    if not student_data:
        raise ValueError(
            f"missing per-student PSEB data for student {student.id} — "
            "regNo must be set before generating an admit card"
        )

    # Roll number falls through to the Student row when the per-student
    # override is blank; regNo stays mandatory (no equivalent on Student).
    roll_no = student_data.get("rollNo") or student.roll_no
    if not roll_no:
        raise ValueError(
            f"missing rollNo for student {student.id} — set it on the Student record "
            "or in the per-student PSEB data before generating an admit card"
        )
    reg_no = student_data.get("regNo")
    if not reg_no:
        raise ValueError(
            f"missing regNo for student {student.id} — set it in the per-student PSEB data"
        )

    today = DateT.today()
    candidate = PsebCandidate(
        rollNo=roll_no,
        regNo=reg_no,
        name=_bi(student.name),
        fatherName=_bi(student.father),
        motherName=_bi(student.mother),
        dob=student.dob or DateT(2010, 1, 1),
        differentlyAbled=student_data.get("differentlyAbled", "N.A."),
        category=student_data.get("category", "Regular"),
        photoUrl=None,
    )

    return PsebAdmitCard(
        schoolCode=template_data["schoolCode"],
        studentId=f"KIS-{student.id}",
        centre=template_data["centre"],
        candidate=candidate,
        examTime=template_data["examTime"],
        practicalDateRange=template_data.get("practicalDateRange"),
        dateSheet=template_data["dateSheet"],
        instructions=template_data.get("instructions", []),
        examName=template_data.get("examName"),
        printedOn=today,
        documentId=f"ADM/{session}/{student.id:04d}",
    )
