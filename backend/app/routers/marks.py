import re
from collections import defaultdict
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from ..constants import CLASSES, canonical_class
from ..deps import db_dep, current_user, CurrentUser, assert_class_allowed, require_admin, require_menu
from ..events import broker
from ..schemas.marks import MarkOut
from ..schemas.results import (
    AttendanceOut, CellOut, ClassResultsOut, ComponentInfoOut, ComponentMarkOut, GroupColumnOut,
    SessionDatesOut, StudentResultOut, SubjectColumnOut, SubjectResultOut,
)
from ..models.marks import Marks
from ..models.marks_batch import MarksBatch, MarksBatchStatus
from ..models.class_subject import ClassSubject, SubjectExamComponent
from ..models.student import Student
from ..models.record_status import RecordStatus
from ..services.report_cards import resolve_template
from ..services.results import (
    CONDITIONAL_MAX_FAILS_DEFAULT, GRADE_LETTERS, PASS_PCT_DEFAULT, aggregate_class_results,
    normalize_grade_letter,
)
from ..services.marks_batches import batch_status_map, find_batch, upsert_batch_marks
from ..services.roster import roll_sort_key
from ..services.attendance_summary import attendance_summary
from ..services.sessions import get_session, scope_dates
from ..logging_config import get_logger
from ._bulk import parse_csv, must_str, opt_str, must_int, FieldError, error_dict

router = APIRouter(prefix="/marks", tags=["marks"])
log = get_logger("app.audit.marks")


SESSION_RE = re.compile(r"^\d{4}-\d{2}$")   # academic session, e.g. 2026-27


@router.post("/bulk", status_code=410)
def save_bulk_gone(user: CurrentUser = Depends(current_user)):
    """Retired: wrote marks outside the draft/submit batch workflow. Nothing in
    the web or mobile apps calls it; Marks Entry uses POST /marks/batches."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="POST /marks/bulk is retired. Save marks through POST /marks/batches (Marks Entry).",
    )


@router.get("/results", response_model=ClassResultsOut)
def class_results(
    class_name: str = Query(alias="class"),
    session: str = Query(),
    scope: Literal["term1", "term2", "annual"] = Query(default="annual"),
    include_drafts: bool = Query(default=True),
    with_attendance: bool = Query(default=True),
    user: CurrentUser = Depends(require_menu("marks-results", "results")),
    db: Session = Depends(db_dep),
):
    """Component-aware results for a class and session, rolled up to per-subject
    totals within the scope (Term 1 / Term 2 / Annual), with rank, pass status,
    per-exam columns, batch status and attendance for the scope's dates.

    `include_drafts=true` (default) counts marks whose batch is still a draft and
    flags them; false leaves them out, which is what report cards do.
    """
    assert_class_allowed(user, class_name)

    subjects = db.execute(
        select(ClassSubject)
        .where(ClassSubject.class_name == class_name)
        .options(selectinload(ClassSubject.components))
        .order_by(ClassSubject.order_index, ClassSubject.subject_name)
    ).scalars().all()

    students = sorted(
        db.execute(
            select(Student.id, Student.name, Student.roll_no, Student.status)
            .where(Student.class_name == class_name, Student.status != RecordStatus.deleted)
        ).all(),
        key=lambda s: roll_sort_key(s.roll_no, s.name),
    )
    info_by_id = {s.id: s for s in students}
    student_ids = [s.id for s in students]

    marks_rows = db.execute(
        select(Marks).where(Marks.class_name == class_name, Marks.session == session)
    ).scalars().all()

    # Same pass/promotion rule as the class's report card, so screen and card agree.
    template = resolve_template(db, class_name=class_name, session=session, scope=scope)
    rule = ((template.data or {}).get("promotionRule") if template else None) or {}
    agg = aggregate_class_results(
        class_name=class_name, session=session, scope=scope,
        class_subjects=subjects, marks_rows=marks_rows, student_ids=student_ids,
        batch_status_by_key=batch_status_map(db, class_name, session),
        include_drafts=include_drafts,
        pass_pct=float(rule.get("passPct", PASS_PCT_DEFAULT)),
        conditional_max_fails=int(rule.get("conditionalMaxFails", CONDITIONAL_MAX_FAILS_DEFAULT)),
    )

    warnings = list(agg.warnings)
    attendance: dict[int, Any] = {}
    session_dates = None
    session_row = get_session(db, session)
    if session_row is None:
        warnings.append(f"Session {session} is not configured, so attendance is not shown.")
    else:
        start, end = scope_dates(session_row, scope)
        session_dates = SessionDatesOut(start=start.isoformat(), end=end.isoformat())
        if with_attendance:
            attendance = attendance_summary(db, student_ids=student_ids, start=start, end=end)

    return ClassResultsOut(
        class_name=agg.class_name,
        session=agg.session,
        scope=agg.scope,
        subject_columns=[
            SubjectColumnOut(
                subject_name=c.subject_name, subject_name_pa=c.subject_name_pa,
                category=c.category, order_index=c.order_index, max=c.max,
                is_grading=c.is_grading, batch_status=c.batch_status,
                components=[ComponentInfoOut(**vars(ci)) for ci in c.components],
            )
            for c in agg.subject_columns
        ],
        groups=[GroupColumnOut(**vars(g)) for g in agg.groups],
        students=[_student_out(sr, info_by_id[sr.student_id], attendance.get(sr.student_id))
                  for sr in agg.students],
        class_size=agg.class_size,
        ranked_count=agg.ranked_count,
        include_drafts=agg.include_drafts,
        has_drafts=agg.has_drafts,
        complete=agg.complete,
        engine_version=agg.engine_version,
        session_dates=session_dates,
        warnings=warnings,
    )


def _student_out(sr, info, att) -> StudentResultOut:
    return StudentResultOut(
        student_id=sr.student_id,
        name=info.name,
        roll_no=info.roll_no,
        status=getattr(info.status, "value", info.status),
        subjects=[
            SubjectResultOut(
                subject_name=s.subject_name, category=s.category,
                obtained=s.obtained, max=s.max, percentage=s.percentage,
                grade=s.grade, status=s.status,
                is_grading=s.is_grading, grade_letter=s.grade_letter, term_letters=s.term_letters,
                batch_status=s.batch_status,
                components_total=s.components_total, components_marked=s.components_marked,
                components=[ComponentMarkOut(**vars(cm)) for cm in s.components],
                cells=[CellOut(key=c.key, obtained=c.obtained, max=c.max, marked=c.marked,
                               total=c.total, status=c.status) for c in s.cells],
            )
            for s in sr.subjects
        ],
        total_obtained=sr.total_obtained, total_max=sr.total_max,
        percentage=sr.percentage, grade=sr.grade,
        has_marks=sr.has_marks, rank=sr.rank, pass_status=sr.pass_status,
        failed_subjects=sr.failed_subjects, promotion=sr.promotion,
        draft_components=sr.draft_components,
        attendance=AttendanceOut(**vars(att)) if att is not None else None,
    )


@router.get("", response_model=list[MarkOut])
def list_marks(
    class_name: str = Query(alias="class"),
    exam_type: str = Query(alias="exam_type"),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    assert_class_allowed(user, class_name)
    rows = db.execute(
        select(Marks).where(Marks.class_name == class_name, Marks.exam_type == exam_type)
    ).scalars().all()
    return rows


def _component_max_map(db: Session, class_name: str) -> dict[tuple[str, str], int]:
    """{(subject, component): max_marks} from the class-subjects master for one class."""
    rows = db.execute(
        select(ClassSubject.subject_name, SubjectExamComponent.component_name, SubjectExamComponent.max_marks)
        .join(SubjectExamComponent, SubjectExamComponent.class_subject_id == ClassSubject.id)
        .where(ClassSubject.class_name == class_name)
    ).all()
    return {(r.subject_name, r.component_name): int(r.max_marks) for r in rows}


def _active_student_ids(db: Session, class_name: str) -> set[int]:
    return set(db.scalars(
        select(Student.id).where(Student.class_name == class_name, Student.status != RecordStatus.deleted)
    ))


@router.post("/bulk-import", status_code=201)
def bulk_import_marks(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    """Bulk-import marks (admin only).

    CSV columns: class_name, subject, exam_type, session, student_id, marks,
    grade (optional max_marks). `exam_type` must be one of the subject's exam
    components in Class Subjects, and max marks come from that component.
    Grading exams (max 0, e.g. "Term 1 Grade") take a letter in `grade`
    instead of marks.

    Rows are written through the same draft batches as Marks Entry, so imported
    marks show the draft/submitted state and obey the lock: a row for a
    submitted batch is rejected unless the caller is super-admin. Marks already
    in a batch but absent from the sheet are left untouched.

    Atomic: if any row fails validation, nothing is saved.
    """
    # A plain def (thread pool), not async: the validation and upserts below run
    # hundreds of queries and must not stall the event loop for other requests.
    rows = list(parse_csv(file.file.read()))
    errors: list[dict] = []
    comp_cache: dict[str, dict[tuple[str, str], int]] = {}
    roster_cache: dict[str, set[int]] = {}
    known_sessions: dict[str, bool] = {}
    # (class, subject, component, session) -> {student_id: marks}
    groups: dict[tuple[str, str, str, str], dict[int, int]] = defaultdict(dict)
    group_max: dict[tuple[str, str, str, str], int] = {}
    group_grades: dict[tuple[str, str, str, str], dict[int, str]] = defaultdict(dict)
    group_rows: dict[tuple[str, str, str, str], list[tuple[int, dict]]] = defaultdict(list)

    for i, row in enumerate(rows, start=2):  # row 1 is the header
        try:
            raw_cls = must_str(row, "class_name")
            cls = canonical_class(raw_cls)
            if cls is None:
                raise FieldError("class_name", raw_cls, f"unknown class; expected one of: {', '.join(CLASSES)}")
            try:
                assert_class_allowed(user, cls)
            except HTTPException as he:
                raise FieldError("class_name", cls, str(he.detail)) from None
            subject = must_str(row, "subject")
            exam_type = must_str(row, "exam_type")
            session = must_str(row, "session")
            if not SESSION_RE.match(session):
                raise FieldError("session", session, "must look like 2026-27")
            if session not in known_sessions:
                known_sessions[session] = get_session(db, session) is not None
            if not known_sessions[session]:
                raise FieldError("session", session, "is not an academic session yet (add it on the Sessions page)")

            if cls not in comp_cache:
                comp_cache[cls] = _component_max_map(db, cls)
            comp_max = comp_cache[cls].get((subject, exam_type))
            if comp_max is None:
                raise FieldError(
                    "exam_type", exam_type,
                    f"not an exam component of {subject!r} in {cls} (see Class Subjects)",
                )
            letter: str | None = None
            if comp_max <= 0:
                raw_grade = opt_str(row, "grade")
                letter = normalize_grade_letter(raw_grade)
                if letter is None:
                    raise FieldError("grade", raw_grade, f"this is a graded exam; use one of {', '.join(GRADE_LETTERS)}")
            else:
                max_raw = opt_str(row, "max_marks")
                if max_raw and max_raw != str(comp_max):
                    raise FieldError("max_marks", max_raw, f"must be {comp_max} (set in Class Subjects)")

            student_id = must_int(row, "student_id")
            if cls not in roster_cache:
                roster_cache[cls] = _active_student_ids(db, cls)
            if student_id not in roster_cache[cls]:
                raise FieldError("student_id", str(student_id), f"is not an active student of {cls}")

            if letter is None:
                marks_v = must_int(row, "marks")
                if marks_v < 0 or marks_v > comp_max:
                    raise FieldError("marks", str(marks_v), f"must be between 0 and {comp_max}")
            else:
                marks_v = 0

            key = (cls, subject, exam_type, session)
            if student_id in groups[key]:
                raise FieldError("student_id", str(student_id), "appears twice for the same exam in this file")
            groups[key][student_id] = marks_v
            if letter is not None:
                group_grades[key][student_id] = letter
            group_max[key] = comp_max
            group_rows[key].append((i, row))
        except Exception as e:
            errors.append(error_dict(i, e, row))

    # Lock check: a submitted batch only accepts changes from super-admin.
    batches = {key: find_batch(db, *key) for key in groups}
    if user.role != "super_admin":
        for key, batch in batches.items():
            if batch is not None and batch.status == MarksBatchStatus.submitted:
                for i, row in group_rows[key]:
                    errors.append(error_dict(i, FieldError(
                        "exam_type", key[2],
                        "these marks are submitted (locked); request an edit in Marks Entry first",
                    ), row))

    if errors:
        errors.sort(key=lambda e: e["row"])
        log.warning(
            "bulk import rejected",
            extra={"event": "bulk_import_rejected", "entity": "marks", "rows_total": len(rows), "error_count": len(errors)},
        )
        return {"inserted": 0, "errors": errors, "aborted": True}

    saved = []
    for key, marks_by_student in groups.items():
        cls, subject, exam_type, session = key
        saved.append(upsert_batch_marks(
            db,
            class_name=cls, subject=subject, exam_type=exam_type, session=session,
            max_marks=group_max[key],
            marks_by_student=marks_by_student,
            grades_by_student=group_grades.get(key) if group_max[key] == 0 else None,
            actor=user.name,
            prune_missing=False,
            batch=batches[key],
        ))
    db.commit()
    for b in saved:
        broker.publish("marks_batches", "upsert", id=b.id)
    row_count = sum(len(v) for v in groups.values())
    log.info(
        "bulk import committed",
        extra={"event": "bulk_import_committed", "entity": "marks", "row_count": row_count, "batches": len(saved)},
    )
    return {"inserted": row_count, "errors": [], "aborted": False}
