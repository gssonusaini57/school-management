from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from ..deps import db_dep, current_user, CurrentUser, assert_class_allowed
from ..schemas.marks import MarksBulkCreate, MarkOut
from ..schemas.results import (
    ClassResultsOut, StudentResultOut, SubjectResultOut, SubjectColumnOut,
)
from ..models.marks import Marks
from ..models.class_subject import ClassSubject
from ..models.student import Student
from ..models.record_status import RecordStatus
from ..services.results import aggregate_class_results
from ..logging_config import get_logger
from ._bulk import read_csv, must_str, opt_str, must_int, opt_int, FieldError, error_dict

router = APIRouter(prefix="/marks", tags=["marks"])
log = get_logger("app.audit.marks")


@router.post("/bulk", status_code=201)
def save_bulk(
    payload: MarksBulkCreate,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    assert_class_allowed(user, payload.class_name)
    if payload.max_marks <= 0:
        raise HTTPException(status_code=400, detail="max_marks must be positive")
    over_max = [
        {"student_id": it.student_id, "marks": it.marks, "max_marks": payload.max_marks}
        for it in payload.items
        if it.marks > payload.max_marks or it.marks < 0
    ]
    if over_max:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"{len(over_max)} entries are out of range (0–{payload.max_marks})",
                "rows": over_max[:10],
            },
        )
    for it in payload.items:
        db.add(Marks(
            student_id=it.student_id,
            class_name=payload.class_name,
            exam_type=payload.exam_type,
            subject=payload.subject,
            marks=it.marks,
            max_marks=payload.max_marks,
            session=payload.session,
            saved_by=user.name,
        ))
    db.commit()
    return {"saved": len(payload.items)}


@router.get("/results", response_model=ClassResultsOut)
def class_results(
    class_name: str = Query(alias="class"),
    session: str = Query(),
    scope: Literal["term1", "term2", "annual"] = Query(default="annual"),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Component-aware results for a class+session, rolled up to per-subject
    totals within the chosen scope (Term 1 / Term 2 / Annual). Includes draft
    marks (no batch-status filter); students joined server-side."""
    assert_class_allowed(user, class_name)

    subjects = db.execute(
        select(ClassSubject)
        .where(ClassSubject.class_name == class_name)
        .options(selectinload(ClassSubject.components))
        .order_by(ClassSubject.order_index, ClassSubject.subject_name)
    ).scalars().all()

    students = db.execute(
        select(Student.id, Student.name, Student.roll_no)
        .where(Student.class_name == class_name, Student.status != RecordStatus.deleted)
        .order_by(Student.roll_no.asc(), Student.name.asc())
    ).all()
    name_by_id = {s.id: (s.name, s.roll_no) for s in students}
    student_ids = [s.id for s in students]

    marks_rows = db.execute(
        select(Marks).where(Marks.class_name == class_name, Marks.session == session)
    ).scalars().all()

    agg = aggregate_class_results(
        class_name=class_name, session=session, scope=scope,
        class_subjects=subjects, marks_rows=marks_rows, student_ids=student_ids,
    )

    return ClassResultsOut(
        class_name=agg.class_name,
        session=agg.session,
        scope=agg.scope,
        subject_columns=[
            SubjectColumnOut(
                subject_name=c.subject_name, subject_name_pa=c.subject_name_pa,
                category=c.category, order_index=c.order_index, max=c.max,
            )
            for c in agg.subject_columns
        ],
        students=[
            StudentResultOut(
                student_id=sr.student_id,
                name=name_by_id.get(sr.student_id, ("", None))[0],
                roll_no=name_by_id.get(sr.student_id, ("", None))[1],
                subjects=[
                    SubjectResultOut(
                        subject_name=s.subject_name, category=s.category,
                        obtained=s.obtained, max=s.max, percentage=s.percentage,
                        grade=s.grade, status=s.status,
                    )
                    for s in sr.subjects
                ],
                total_obtained=sr.total_obtained, total_max=sr.total_max,
                percentage=sr.percentage, grade=sr.grade,
            )
            for sr in agg.students
        ],
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


@router.post("/bulk-import", status_code=201)
async def bulk_import_marks(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Bulk-import marks. CSV columns: class_name, exam_type, subject, max_marks, session, student_id, marks.

    Atomic: if any row fails validation, nothing is saved.
    """
    rows = await read_csv(file)
    errors: list[dict] = []
    prepared: list[Marks] = []
    for i, row in enumerate(rows, start=2):
        try:
            cls = must_str(row, "class_name")
            try:
                assert_class_allowed(user, cls)
            except HTTPException as he:
                raise FieldError("class_name", cls, str(he.detail)) from None
            marks_v = opt_int(row, "marks", 0)
            max_v = opt_int(row, "max_marks", 100)
            if max_v <= 0:
                raise FieldError("max_marks", str(max_v), "must be positive")
            if marks_v < 0 or marks_v > max_v:
                raise FieldError("marks", str(marks_v), f"must be between 0 and {max_v}")
            prepared.append(Marks(
                student_id=must_int(row, "student_id"),
                class_name=cls,
                exam_type=must_str(row, "exam_type"),
                subject=must_str(row, "subject"),
                marks=marks_v,
                max_marks=max_v,
                session=opt_str(row, "session"),
                saved_by=user.name,
            ))
        except Exception as e:
            errors.append(error_dict(i, e, row))

    if errors:
        log.warning(
            "bulk import rejected",
            extra={"event": "bulk_import_rejected", "entity": "marks", "rows_total": len(rows), "error_count": len(errors)},
        )
        return {"inserted": 0, "errors": errors, "aborted": True}

    for m in prepared:
        db.add(m)
    db.commit()
    log.info(
        "bulk import committed",
        extra={"event": "bulk_import_committed", "entity": "marks", "row_count": len(prepared)},
    )
    return {"inserted": len(prepared), "errors": [], "aborted": False}
