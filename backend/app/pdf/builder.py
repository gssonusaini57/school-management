"""Build the full validated render payload for a (kind, student) pair.

Report cards: `build_report_card_payload(inputs, student_id)` turns one
student's slice of the class inputs (gathered once per class by
app.services.report_cards) into a validated `ReportCard`. Marks, totals,
rank, class size, attendance and promotion are computed; values typed into
the per-student data override them only when present.

PSEB admit cards: `build_pseb_admit_payload` merges the class template, the
student row and the per-student PSEB identifiers.

Pure functions; no DB access here. Routers and services fetch the rows.
"""
from __future__ import annotations

from datetime import date as DateT
from typing import Any

from .labels import EXAM_GROUP_PA, PROMOTION_LABELS, REPORT_CARD_LABELS, SCOPE_TITLES
from .schemas import (
    Bilingual, BilingualOpt,
    PsebAdmitCard, PsebCandidate,
    ReportCard, ReportCardCell, ReportCardCoScholastic, ReportCardGroup, ReportCardOptions,
    ReportCardSignatures, ReportCardStudent, ReportCardStudentData, ReportCardSubject,
    ReportCardSummary,
)
from ..services.results import grade_legend


def _bi(s: str | None) -> Bilingual:
    """Wrap a single string as a Bilingual{en,pa}, both filled with the
    same text (PSEB admit cards require both)."""
    text = s or "—"
    return Bilingual(en=text, pa=text)


def _opt(en: str | None, pa: str | None = None) -> BilingualOpt:
    """English text with an optional, distinct Punjabi line."""
    en = en or "—"
    return BilingualOpt(en=en, pa=pa if pa and pa != en else None)


def _first(*values: Any) -> Any:
    """The first value that is set (an override, else the computed value); '' counts as unset."""
    for v in values:
        if v is not None and v != "":
            return v
    return None


def printed_attendance(sd: Any, att: Any) -> tuple[float | None, int | None, float | None]:
    """(percentage, working days, days present) to print, treating the three as one unit.

    Overriding a day count recomputes the percentage from the final counts (unless
    the percentage is overridden too); overriding only the percentage hides the
    day counts. A card never prints a percentage that contradicts its own days.
    """
    computed_pct = att.pct if att else None
    computed_wd = att.working_days if att and att.working_days else None
    computed_dp = att.days_present if att and att.working_days else None
    if sd.workingDays is not None or sd.daysPresent is not None:
        wd = _first(sd.workingDays, computed_wd)
        dp = _first(sd.daysPresent, computed_dp)
        if wd is not None and dp is not None and dp > wd:
            # One count overridden, the other computed: they can drift apart as
            # attendance is marked. Refuse rather than print e.g. "160 of 150 days".
            raise ValueError(
                f"attendance override: {dp:g} days present is more than {wd} working days; "
                "correct the attendance override for this student"
            )
        pct = sd.attendancePct
        if pct is None and wd and dp is not None:
            pct = round(dp / wd * 100, 1)
        return pct, wd, dp
    if sd.attendancePct is not None:
        return sd.attendancePct, None, None
    return computed_pct, computed_wd, computed_dp


def build_report_card_payload(inputs: Any, student_id: int, *, photo_url: str | None = None) -> ReportCard:
    """One student's report card from the class inputs.

    Raises ValueError when the card can't be produced (archived, other class,
    or no marks in scope) so the caller reports it for that student only.
    """
    student = inputs.students.get(student_id)
    if student is None:
        raise ValueError(f"student {student_id} is not an active student of {inputs.template.class_name}")
    res = inputs.results_by_student[student_id]
    cr = inputs.class_results
    settings = inputs.settings
    sd = ReportCardStudentData.model_validate(inputs.student_data.get(student_id) or {})

    numeric = [s for s in res.subjects if not s.is_grading]
    grading = [s for s in res.subjects if s.is_grading]
    if not res.has_marks:
        drafts = f" ({res.draft_components} entered marks are still drafts)" if res.draft_components else ""
        raise ValueError(f"no submitted marks for {student.name} in {inputs.scope}{drafts}")

    subjects = [
        ReportCardSubject(
            name=_opt(s.subject_name, s.subject_name_pa),
            marks=s.obtained if s.components_marked else None,
            max=s.max,
            # A grade on a half-entered subject would understate it: only when complete.
            grade=s.grade if s.status == "complete" else None,
            status=s.status,
            cells=[
                ReportCardCell(key=c.key, marks=c.obtained if c.marked else None, max=c.max, status=c.status)
                for c in s.cells
            ],
        )
        for s in numeric
    ]
    groups = [ReportCardGroup(key=g.key, label=_opt(g.key, EXAM_GROUP_PA.get(g.key))) for g in cr.groups]
    co_scholastic = [
        ReportCardCoScholastic(
            name=_opt(s.subject_name, s.subject_name_pa),
            grade=s.grade_letter, term1=s.term_letters.get(1), term2=s.term_letters.get(2),
        )
        for s in grading
    ]

    att = inputs.attendance.get(student_id)
    has_drafts = any(
        cm.batch_status == "draft" and (cm.marks is not None or cm.grade_letter is not None)
        for s in res.subjects for cm in s.components
    )
    incomplete = any(s.status != "complete" for s in res.subjects)
    promotion = _first(sd.promotion, res.promotion)
    default_remarks = settings.get("remarksDefault")
    if sd.remarks is not None:
        remarks = BilingualOpt(en=sd.remarks.en, pa=sd.remarks.pa)
    elif default_remarks:
        remarks = BilingualOpt(en=default_remarks["en"], pa=default_remarks.get("pa"))
    else:
        remarks = None
    att_pct, working_days, days_present = printed_attendance(sd, att)
    # A rank is final only once every classmate's marks are in and submitted.
    rank_provisional = sd.rank is None and not cr.complete

    summary = ReportCardSummary(
        total=res.total_obtained,
        max=res.total_max,
        percentage=res.percentage,
        grade=res.grade if not incomplete else None,
        rank=_first(sd.rank, res.rank),
        classSize=_first(sd.classSize, cr.class_size or None),
        attendancePct=att_pct,
        workingDays=working_days,
        daysPresent=days_present,
        rankProvisional=rank_provisional,
        remarks=remarks,
        promotion=promotion,
        promotionLabel=(BilingualOpt(**PROMOTION_LABELS[promotion]) if promotion in PROMOTION_LABELS
                        else (_opt(promotion) if promotion else None)),
        hasDrafts=has_drafts,
        incomplete=incomplete,
        failedSubjects=res.failed_subjects,
    )

    sig = settings.get("signatures") or {}
    admission = _first(sd.admissionNo, student.admission_id,
                       str(student.admission_no) if student.admission_no else None)
    return ReportCard(
        session=inputs.template.session,
        term=inputs.template.term,
        scope=inputs.scope,
        layout=inputs.template.layout or "summary",
        title=BilingualOpt(**SCOPE_TITLES[inputs.scope]),
        student=ReportCardStudent(
            name=_opt(student.name),
            **{"class": student.class_name},
            rollNo=student.roll_no,
            fatherName=_opt(student.father),
            motherName=_opt(student.mother),
            dob=student.dob,
            house=sd.house or inputs.houses.get(student_id),
            admissionNo=admission,
            photoUrl=photo_url,
        ),
        groups=groups,
        subjects=subjects,
        coScholastic=co_scholastic,
        summary=summary,
        signatures=ReportCardSignatures(
            classTeacher=sig.get("classTeacher"), examIncharge=sig.get("examIncharge"),
            principal=sig.get("principal"),
        ),
        options=ReportCardOptions(
            showAttendance=settings.get("showAttendance", True), showRank=settings.get("showRank", True),
            showPhoto=settings.get("showPhoto", True), showGradingScale=settings.get("showGradingScale", True),
        ),
        labels={k: BilingualOpt(**v) for k, v in REPORT_CARD_LABELS.items()},
        gradeLegend=grade_legend(),
        generatedOn=DateT.today(),
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
    if student.dob is None:
        # An admit card is a board document: never print an invented date of birth.
        raise ValueError(f"{student.name} has no date of birth on record; add it before printing the admit card")
    candidate = PsebCandidate(
        rollNo=roll_no,
        regNo=reg_no,
        name=_bi(student.name),
        fatherName=_bi(student.father),
        motherName=_bi(student.mother),
        dob=student.dob,
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
