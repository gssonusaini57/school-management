from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..deps import db_dep, current_user, CurrentUser, assert_class_allowed
from ..schemas.marks import MarksBulkCreate, MarkOut
from ..models.marks import Marks
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
            prepared.append(Marks(
                student_id=must_int(row, "student_id"),
                class_name=cls,
                exam_type=must_str(row, "exam_type"),
                subject=must_str(row, "subject"),
                marks=opt_int(row, "marks", 0),
                max_marks=opt_int(row, "max_marks", 100),
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
