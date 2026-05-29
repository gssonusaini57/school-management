from datetime import datetime
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from ..deps import db_dep, current_user, CurrentUser, assert_class_allowed, require_admin
from ..schemas.student import (
    StudentCreate, StudentUpdate, StudentOut, StudentPage, DeleteRequestBody,
)
from ..models.student import Student
from ..models.document import StudentDocument, DocumentKind
from ..models.record_status import RecordStatus
from ..models.student_edit_request import StudentEditRequest, EditRequestStatus, EditRequestRole
from ..events import broker
from ..logging_config import get_logger
from ._bulk import read_csv, title_case, parse_date_field, must_str, opt_str, FieldError, error_dict

router = APIRouter(prefix="/students", tags=["students"])
log = get_logger("app.audit.students")


def _has(db: Session, sid: int, kind: DocumentKind) -> bool:
    return db.execute(
        select(func.count(StudentDocument.id)).where(
            StudentDocument.student_id == sid, StudentDocument.kind == kind
        )
    ).scalar_one() > 0


def _to_out(db: Session, s: Student) -> StudentOut:
    out = StudentOut.model_validate(s)
    out.has_photo = _has(db, s.id, DocumentKind.photo)
    out.has_dob_cert = _has(db, s.id, DocumentKind.dob_cert)
    out.has_aadhar = _has(db, s.id, DocumentKind.aadhar)
    return out


def _decorate_pending_edit(db: Session, out: StudentOut, sid: int) -> StudentOut:
    """Single-row decoration: surface the full pending-edit metadata."""
    req = db.execute(
        select(StudentEditRequest)
        .where(
            StudentEditRequest.student_id == sid,
            StudentEditRequest.status == EditRequestStatus.pending,
        )
        .order_by(StudentEditRequest.requested_at.desc())
        .limit(1)
    ).scalars().first()
    if req:
        out.has_pending_edit = True
        out.pending_edit_request_id = req.id
        out.pending_edit_requested_by = req.requested_by
        out.pending_edit_requested_at = req.requested_at
    return out


def _decorate_list_pending_edits(db: Session, items: list[StudentOut]) -> None:
    """Batch-decorate `has_pending_edit` on a list response with one query.

    Avoids N+1 by collecting all student ids on the page and looking up the
    set of those with a pending edit. The full requester/timestamp fields stay
    null on list rows (only the single-row reader populates them).
    """
    ids = [i.id for i in items]
    if not ids:
        return
    rows = db.execute(
        select(StudentEditRequest.student_id)
        .where(
            StudentEditRequest.student_id.in_(ids),
            StudentEditRequest.status == EditRequestStatus.pending,
        )
        .distinct()
    ).scalars().all()
    pending_ids = set(rows)
    for it in items:
        if it.id in pending_ids:
            it.has_pending_edit = True


def _jsonify(v):
    """Coerce DB / Pydantic values to JSON-safe primitives for the diff blob."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, Decimal):
        return str(v)
    # date / datetime
    iso = getattr(v, "isoformat", None)
    if callable(iso):
        return iso()
    return str(v)


def _compute_admission_id(year: int, admission_no: int | None) -> str | None:
    if admission_no is None:
        return None
    return f"KIS/{year:04d}/{admission_no:04d}"


def _check_uniqueness(
    db: Session,
    *,
    admission_id: str | None,
    class_name: str | None,
    roll_no: str | None,
    exclude_id: int | None = None,
) -> None:
    """Pre-flight check so we can return a 409 with the conflicting student's
    name instead of a generic IntegrityError. Race-condition safety net is the
    DB UNIQUE indexes themselves."""
    if admission_id:
        q = select(Student.id, Student.name).where(Student.admission_id == admission_id)
        if exclude_id is not None:
            q = q.where(Student.id != exclude_id)
        row = db.execute(q).first()
        if row:
            raise HTTPException(
                status_code=409,
                detail=f"Admission ID {admission_id} is already used by {row.name} (#{row.id})",
            )
    if class_name and roll_no:
        q = select(Student.id, Student.name).where(
            Student.class_name == class_name, Student.roll_no == roll_no
        )
        if exclude_id is not None:
            q = q.where(Student.id != exclude_id)
        row = db.execute(q).first()
        if row:
            raise HTTPException(
                status_code=409,
                detail=f"Roll number {roll_no} in {class_name} is already used by {row.name} (#{row.id})",
            )


@router.get("", response_model=StudentPage)
def list_students(
    class_name: str | None = Query(default=None, alias="class"),
    q: str | None = Query(default=None, description="Search across name/father/phone/village"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=1000),
    include_deleted: bool = Query(default=False),
    status: str | None = Query(default=None, description="Filter by record status (e.g. pending_delete)"),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    stmt = select(Student)
    if class_name:
        assert_class_allowed(user, class_name)
        stmt = stmt.where(Student.class_name == class_name)
    elif user.role == "staff" and user.allowed_classes:
        stmt = stmt.where(Student.class_name.in_(user.allowed_classes))
    # Status filter takes precedence over the default "hide deleted" rule
    # so the UI can ask explicitly for the pending_delete subset.
    if status == "pending_delete":
        stmt = stmt.where(Student.status == RecordStatus.pending_delete)
    elif status == "active":
        stmt = stmt.where(Student.status == RecordStatus.active)
    elif not (include_deleted and user.role == "super_admin"):
        # Default: hide fully-deleted rows from everyone except super-admin opt-in.
        stmt = stmt.where(Student.status != RecordStatus.deleted)
    if q:
        needle = f"%{q.strip()}%"
        if needle != "%%":
            stmt = stmt.where(
                or_(
                    Student.name.ilike(needle),
                    Student.father.ilike(needle),
                    Student.phone.ilike(needle),
                    Student.village.ilike(needle),
                    Student.admission_id.ilike(needle),
                )
            )

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()

    rows = db.execute(
        stmt.order_by(Student.class_name.asc(), Student.roll_no.asc(), Student.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
    ).scalars().all()

    items = [_to_out(db, s) for s in rows]
    _decorate_list_pending_edits(db, items)
    return StudentPage(
        items=items,
        total=int(total),
        page=page,
        page_size=page_size,
    )


@router.get("/{sid}", response_model=StudentOut)
def get_student(sid: int, user: CurrentUser = Depends(current_user), db: Session = Depends(db_dep)):
    s = db.get(Student, sid)
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    if s.status == RecordStatus.deleted and user.role != "super_admin":
        raise HTTPException(status_code=404, detail="Not found")
    assert_class_allowed(user, s.class_name)
    return _decorate_pending_edit(db, _to_out(db, s), s.id)


@router.post("", response_model=StudentOut, status_code=201)
def create_student(
    payload: StudentCreate,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    assert_class_allowed(user, payload.class_name)
    year = datetime.utcnow().year
    admission_id = _compute_admission_id(year, payload.admission_no)
    _check_uniqueness(
        db,
        admission_id=admission_id,
        class_name=payload.class_name,
        roll_no=payload.roll_no or None,
    )
    s = Student(
        **payload.model_dump(),
        admission_id=admission_id,
        added_by=user.name,
        updated_by=user.name,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    broker.publish("students", "upsert", id=s.id, class_name=s.class_name)
    broker.publish("dashboard", "students_changed")
    log.info(
        "student created",
        extra={"event": "student_created", "student_id": s.id, "class_name": s.class_name, "student_name": s.name},
    )
    return _to_out(db, s)


@router.patch("/{sid}", response_model=StudentOut)
def update_student(
    sid: int,
    payload: StudentUpdate,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Edit a student.

    - Super-admin: applies immediately (legacy behaviour).
    - Admin / Staff: queued to `student_edit_requests` for super-admin review.
      One pending request per student at a time; a second submitter gets 409.
      Uniqueness collisions on admission_no/class_name/roll_no surface as 409
      at queue time, not later.
    """
    s = db.get(Student, sid)
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    if s.status == RecordStatus.deleted and user.role != "super_admin":
        raise HTTPException(status_code=404, detail="Not found")
    assert_class_allowed(user, s.class_name)

    updates = payload.model_dump(exclude_unset=True)
    # Skip no-ops: only keep fields whose values actually differ from the row.
    diff_fields = {k: v for k, v in updates.items() if getattr(s, k) != v}
    if not diff_fields:
        return _decorate_pending_edit(db, _to_out(db, s), s.id)

    if user.role == "super_admin":
        for k, v in diff_fields.items():
            setattr(s, k, v)
        if "admission_no" in diff_fields:
            year = (s.created_at or datetime.utcnow()).year
            s.admission_id = _compute_admission_id(year, s.admission_no)
        if any(k in diff_fields for k in ("admission_no", "class_name", "roll_no")):
            _check_uniqueness(
                db,
                admission_id=s.admission_id,
                class_name=s.class_name,
                roll_no=s.roll_no or None,
                exclude_id=s.id,
            )
        s.updated_by = user.name
        db.commit()
        db.refresh(s)
        broker.publish("students", "upsert", id=s.id, class_name=s.class_name)
        log.info(
            "student updated",
            extra={
                "event": "student_updated",
                "student_id": s.id,
                "class_name": s.class_name,
                "fields": list(diff_fields.keys()),
                "actor": user.name,
            },
        )
        return _decorate_pending_edit(db, _to_out(db, s), s.id)

    # Staff / admin → queue for super-admin approval.
    existing_pending = db.execute(
        select(StudentEditRequest).where(
            StudentEditRequest.student_id == sid,
            StudentEditRequest.status == EditRequestStatus.pending,
        )
    ).scalar_one_or_none()
    if existing_pending:
        raise HTTPException(
            status_code=409,
            detail="An edit request is already pending super-admin review for this student.",
        )

    # Surface uniqueness collisions now (apply the change in-memory to compute
    # the would-be admission_id, then rollback any in-memory mutations).
    if any(k in diff_fields for k in ("admission_no", "class_name", "roll_no")):
        prospective_admission_no = diff_fields.get("admission_no", s.admission_no)
        prospective_class = diff_fields.get("class_name", s.class_name)
        prospective_roll = diff_fields.get("roll_no", s.roll_no)
        year = (s.created_at or datetime.utcnow()).year
        prospective_admission_id = _compute_admission_id(year, prospective_admission_no)
        _check_uniqueness(
            db,
            admission_id=prospective_admission_id,
            class_name=prospective_class,
            roll_no=prospective_roll or None,
            exclude_id=s.id,
        )

    changes_blob = {
        k: {"old": _jsonify(getattr(s, k)), "new": _jsonify(v)}
        for k, v in diff_fields.items()
    }
    req = StudentEditRequest(
        student_id=sid,
        requested_at=datetime.utcnow(),
        requested_by=user.name,
        requested_by_role=EditRequestRole.admin if user.role == "admin" else EditRequestRole.staff,
        changes=changes_blob,
        status=EditRequestStatus.pending,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    broker.publish("edit_requests", "upsert", id=req.id)
    broker.publish("students", "upsert", id=s.id, class_name=s.class_name)
    notify_student_edit_request(db, req, s)
    log.warning(
        "student_edit_requested",
        extra={
            "event": "student_edit_requested",
            "edit_request_id": req.id,
            "student_id": s.id,
            "class_name": s.class_name,
            "fields": list(diff_fields.keys()),
            "actor": user.name,
        },
    )
    # Return the unchanged student decorated with the new pending-edit marker.
    return _decorate_pending_edit(db, _to_out(db, s), s.id)


@router.delete("/{sid}", response_model=StudentOut)
def delete_student(
    sid: int,
    body: DeleteRequestBody | None = Body(default=None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Soft-delete request workflow.

    - Staff           → must own the class; status `active` → `pending_delete`.
    - Admin           → status `active` → `pending_delete`. Returns the updated row.
    - Super-admin     → status `pending_delete`/`active` → `deleted` directly.
                        Hard-delete (purge) is a separate endpoint:
                        DELETE /api/admin/deletion-requests/student/{id}.
    """
    s = db.get(Student, sid)
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    if s.status == RecordStatus.deleted and user.role != "super_admin":
        raise HTTPException(status_code=404, detail="Not found")
    # Staff can only request deletion within their assigned class scope.
    assert_class_allowed(user, s.class_name)

    reason = (body.reason if body else None) or None
    now = datetime.utcnow()

    if user.role == "super_admin":
        # Super-admin's delete moves straight to `deleted` (archived).
        # If admin/staff had already requested, preserve the request audit columns.
        if s.status == RecordStatus.active:
            s.delete_requested_at = now
            s.delete_requested_by = user.name
            if reason:
                s.delete_reason = reason
        elif s.status == RecordStatus.pending_delete and reason:
            # Super-admin can amend reason at approve time.
            s.delete_reason = reason
        s.status = RecordStatus.deleted
        s.deleted_at = now
        s.deleted_by = user.name
        event = "student_archived"
    else:  # admin or staff
        if s.status != RecordStatus.active:
            raise HTTPException(status_code=409, detail="Already pending deletion or deleted")
        s.status = RecordStatus.pending_delete
        s.delete_requested_at = now
        s.delete_requested_by = user.name
        s.delete_reason = reason
        event = "student_delete_requested"

    db.commit()
    db.refresh(s)
    broker.publish("students", "upsert", id=sid, class_name=s.class_name)
    broker.publish("deletion_requests", "upsert", kind="student", id=sid)
    broker.publish("dashboard", "students_changed")
    log.warning(
        event,
        extra={
            "event": event,
            "student_id": sid,
            "class_name": s.class_name,
            "student_name": s.name,
            "actor": user.name,
            "reason": reason,
        },
    )
    return _to_out(db, s)


@router.post("/{sid}/documents/{kind}", status_code=204)
async def upload_document(
    sid: int,
    kind: DocumentKind = Path(...),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    s = db.get(Student, sid)
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    if s.status == RecordStatus.deleted and user.role != "super_admin":
        raise HTTPException(status_code=404, detail="Student not found")
    assert_class_allowed(user, s.class_name)
    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty file")
    existing = db.execute(
        select(StudentDocument).where(
            StudentDocument.student_id == sid, StudentDocument.kind == kind
        )
    ).scalar_one_or_none()
    if existing:
        existing.mime_type = file.content_type or "application/octet-stream"
        existing.byte_size = len(blob)
        existing.data = blob
    else:
        db.add(StudentDocument(
            student_id=sid,
            kind=kind,
            mime_type=file.content_type or "application/octet-stream",
            byte_size=len(blob),
            data=blob,
        ))
    db.commit()
    broker.publish("students", "upsert", id=sid, class_name=s.class_name)


@router.post("/bulk-import", status_code=201)
async def bulk_import_students(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    """Bulk-import students from a CSV. Headers must match the template.

    Atomic: if any row fails validation, nothing is saved — admin fixes the
    sheet and re-uploads.
    """
    rows = await read_csv(file)
    errors: list[dict] = []
    prepared: list[Student] = []
    year = datetime.utcnow().year
    # Track within-batch collisions so two rows in the same upload can't both
    # claim the same admission_id or (class, roll_no).
    seen_admission_ids: set[str] = set()
    seen_class_rolls: set[tuple[str, str]] = set()
    for i, row in enumerate(rows, start=2):  # row 1 is header
        try:
            phone = must_str(row, "phone")
            if not phone.isdigit() or len(phone) != 10:
                raise FieldError("phone", phone, "must be exactly 10 digits")
            aadhar = opt_str(row, "aadhar")
            if aadhar and (not aadhar.isdigit() or len(aadhar) != 12):
                raise FieldError("aadhar", aadhar, "must be exactly 12 digits when provided")
            cls = must_str(row, "class_name")
            try:
                assert_class_allowed(user, cls)
            except HTTPException as he:
                raise FieldError("class_name", cls, str(he.detail)) from None
            fee_raw = opt_str(row, "annual_fee", "0") or "0"
            try:
                fee = Decimal(fee_raw)
            except InvalidOperation:
                raise FieldError("annual_fee", fee_raw, "must be a number") from None

            admission_no_raw = opt_str(row, "admission_no")
            admission_no_val: int | None = None
            if admission_no_raw:
                try:
                    admission_no_val = int(admission_no_raw)
                except ValueError:
                    raise FieldError("admission_no", admission_no_raw, "must be an integer") from None
            roll_no_val = opt_str(row, "roll_no") or None
            admission_id_val = _compute_admission_id(year, admission_no_val)

            # Within-batch dedup
            if admission_id_val and admission_id_val in seen_admission_ids:
                raise FieldError("admission_no", str(admission_no_val), "duplicate admission number within this upload")
            if roll_no_val and (cls, roll_no_val) in seen_class_rolls:
                raise FieldError("roll_no", roll_no_val, f"duplicate roll number for class {cls} within this upload")

            # Against existing DB rows
            try:
                _check_uniqueness(
                    db,
                    admission_id=admission_id_val,
                    class_name=cls,
                    roll_no=roll_no_val,
                )
            except HTTPException as he:
                raise FieldError("admission_no/roll_no", "", str(he.detail)) from None

            if admission_id_val:
                seen_admission_ids.add(admission_id_val)
            if roll_no_val:
                seen_class_rolls.add((cls, roll_no_val))

            prepared.append(Student(
                name=title_case(must_str(row, "name")),
                father=title_case(must_str(row, "father")),
                mother=title_case(must_str(row, "mother")),
                dob=parse_date_field(opt_str(row, "dob"), field="dob"),
                gender=opt_str(row, "gender", "Male"),
                village=opt_str(row, "village"),
                phone=phone,
                aadhar=aadhar,
                alt_phone=opt_str(row, "alt_phone", "N/A"),
                religion=opt_str(row, "religion", "N/A"),
                prev_school=opt_str(row, "prev_school", "N/A"),
                bank_name=opt_str(row, "bank_name", "N/A"),
                bank_acc=opt_str(row, "bank_acc", "N/A"),
                bank_ifsc=opt_str(row, "bank_ifsc", "N/A").upper(),
                annual_fee=fee,
                class_name=cls,
                admission_no=admission_no_val,
                admission_id=admission_id_val,
                roll_no=roll_no_val,
                added_by=user.name,
                updated_by=user.name,
            ))
        except Exception as e:
            errors.append(error_dict(i, e, row))

    if errors:
        log.warning(
            "bulk import rejected",
            extra={"event": "bulk_import_rejected", "entity": "students", "rows_total": len(rows), "error_count": len(errors)},
        )
        return {"inserted": 0, "errors": errors, "aborted": True}

    for s in prepared:
        db.add(s)
    db.commit()
    if prepared:
        broker.publish("students", "upsert", id=0)
        broker.publish("dashboard", "students_changed")
    log.info(
        "bulk import committed",
        extra={"event": "bulk_import_committed", "entity": "students", "row_count": len(prepared)},
    )
    return {"inserted": len(prepared), "errors": [], "aborted": False}
