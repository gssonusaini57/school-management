"""Per-class subject master + nested exam-component CRUD.

Super-admin owns all writes (subjects, components, seeding). All authenticated
users can read so MarksEntry can dropdown the subject names + components.

Routes:
  GET    /class-subjects                — list all (optional ?class=)
  POST   /class-subjects                — create subject
  GET    /class-subjects/{id}           — fetch subject + components
  PATCH  /class-subjects/{id}           — update subject
  DELETE /class-subjects/{id}           — delete subject (cascades components)
  POST   /class-subjects/bulk-import    — CSV upload (subjects only)
  POST   /class-subjects/seed-defaults  — seed PDF exam-pattern across all classes

  POST   /class-subjects/{id}/components            — add component
  PATCH  /class-subjects/components/{cid}           — update component
  DELETE /class-subjects/components/{cid}           — delete component
  PUT    /class-subjects/{id}/components            — REPLACE all components atomically
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..deps import db_dep, current_user, require_super_admin, CurrentUser
from ..models.class_subject import ClassSubject, SubjectExamComponent, SubjectCategory
from ..schemas.class_subject import (
    ClassSubjectCreate, ClassSubjectUpdate, ClassSubjectOut, ClassSubjectDetailOut,
    ExamComponentCreate, ExamComponentUpdate, ExamComponentOut, ComponentsReplaceBody,
)
from ..events import broker
from ..logging_config import get_logger
from ..seed.exam_pattern import EXAM_PATTERN_SEED
from ._bulk import read_csv, must_str, opt_str, FieldError, error_dict

router = APIRouter(prefix="/class-subjects", tags=["class-subjects"])
log = get_logger("app.audit.class_subjects")


# ── Subject endpoints ────────────────────────────────────────────
@router.get("", response_model=list[ClassSubjectOut])
def list_subjects(
    class_name: str | None = Query(default=None, alias="class"),
    _user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    stmt = select(ClassSubject)
    if class_name:
        stmt = stmt.where(ClassSubject.class_name == class_name)
    stmt = stmt.order_by(ClassSubject.class_name, ClassSubject.order_index, ClassSubject.subject_name)
    return db.execute(stmt).scalars().all()


@router.get("/{subject_id}", response_model=ClassSubjectDetailOut)
def get_subject(
    subject_id: int,
    _user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    row = db.execute(
        select(ClassSubject)
        .where(ClassSubject.id == subject_id)
        .options(selectinload(ClassSubject.components))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Subject not found")
    return row


@router.post("", response_model=ClassSubjectOut, status_code=201)
def create_subject(
    payload: ClassSubjectCreate,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    row = ClassSubject(
        class_name=payload.class_name.strip(),
        subject_name=payload.subject_name.strip(),
        subject_name_pa=(payload.subject_name_pa or "").strip() or None,
        category=SubjectCategory(payload.category),
        order_index=payload.order_index,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"{row.subject_name} already exists for {row.class_name}")
    db.refresh(row)
    broker.publish("class_subjects", "upsert", id=row.id)
    log.info(
        "class subject created",
        extra={"event": "class_subject_created", "subject_id": row.id, "class_name": row.class_name, "subject": row.subject_name, "actor": user.name},
    )
    return row


@router.patch("/{subject_id}", response_model=ClassSubjectOut)
def update_subject(
    subject_id: int,
    payload: ClassSubjectUpdate,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    row = db.get(ClassSubject, subject_id)
    if not row:
        raise HTTPException(status_code=404, detail="Subject not found")
    data = payload.model_dump(exclude_unset=True)
    if "subject_name" in data and data["subject_name"]:
        row.subject_name = data["subject_name"].strip()
    if "subject_name_pa" in data:
        v = (data["subject_name_pa"] or "").strip()
        row.subject_name_pa = v or None
    if "category" in data and data["category"] is not None:
        row.category = SubjectCategory(data["category"])
    if "order_index" in data and data["order_index"] is not None:
        row.order_index = data["order_index"]
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"{row.subject_name} already exists for {row.class_name}")
    db.refresh(row)
    broker.publish("class_subjects", "upsert", id=row.id)
    log.info(
        "class subject updated",
        extra={"event": "class_subject_updated", "subject_id": row.id, "actor": user.name},
    )
    return row


@router.delete("/{subject_id}", status_code=204)
def delete_subject(
    subject_id: int,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    row = db.get(ClassSubject, subject_id)
    if not row:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.delete(row)
    db.commit()
    broker.publish("class_subjects", "delete", id=subject_id)
    log.info(
        "class subject deleted",
        extra={"event": "class_subject_deleted", "subject_id": subject_id, "actor": user.name},
    )


@router.post("/bulk-import", status_code=201)
async def bulk_import_subjects(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    """CSV columns: class_name, subject_name, subject_name_pa, category, order_index.

    Atomic: any row failure rolls back the whole file. Components are managed
    separately (use the per-subject detail page or seed-defaults).
    """
    rows = await read_csv(file)
    errors: list[dict] = []
    prepared: list[ClassSubject] = []
    seen: set[tuple[str, str]] = set()
    valid_cats = {c.value for c in SubjectCategory}
    for i, row in enumerate(rows, start=2):
        try:
            cls = must_str(row, "class_name")
            sub = must_str(row, "subject_name")
            key = (cls.lower(), sub.lower())
            if key in seen:
                raise FieldError("subject_name", sub, f"duplicate of an earlier row for {cls}")
            seen.add(key)
            cat = opt_str(row, "category", "academic")
            if cat not in valid_cats:
                raise FieldError("category", cat, f"must be one of {', '.join(sorted(valid_cats))}")
            try:
                order_raw = (row.get("order_index") or "").strip()
                order = int(order_raw) if order_raw else 0
            except ValueError:
                raise FieldError("order_index", row.get("order_index", ""), "must be a whole number") from None
            prepared.append(ClassSubject(
                class_name=cls,
                subject_name=sub,
                subject_name_pa=opt_str(row, "subject_name_pa") or None,
                category=SubjectCategory(cat),
                order_index=order,
            ))
        except Exception as e:
            errors.append(error_dict(i, e, row))

    if errors:
        return {"inserted": 0, "errors": errors, "aborted": True}

    for r in prepared:
        db.add(r)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        return {
            "inserted": 0,
            "errors": [{"row": None, "field": None, "value": None, "reason": f"DB rejected: {e.orig}", "data": {}}],
            "aborted": True,
        }
    broker.publish("class_subjects", "bulk", id=0)
    log.info(
        "class subjects bulk import committed",
        extra={"event": "bulk_import_committed", "entity": "class_subjects", "row_count": len(prepared), "actor": user.name},
    )
    return {"inserted": len(prepared), "errors": [], "aborted": False}


@router.post("/seed-defaults", status_code=201)
def seed_defaults(
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    """Seed the KIS-default exam pattern across all classes (NUR through 12th).

    Refuses if any class_subjects row already exists — re-run safe but won't
    overwrite manual edits. Super-admin must clear the master first if they
    really want to re-seed.
    """
    existing = db.execute(select(ClassSubject.id).limit(1)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Subjects already exist. Clear the class-subjects master before seeding.",
        )

    inserted_subjects = 0
    inserted_components = 0
    for s in EXAM_PATTERN_SEED:
        subject = ClassSubject(
            class_name=s["class_name"],
            subject_name=s["subject_name"],
            subject_name_pa=s["subject_name_pa"],
            category=SubjectCategory(s["category"]),
            order_index=s["order_index"],
        )
        db.add(subject)
        db.flush()  # get subject.id for FK
        for c in s["components"]:
            db.add(SubjectExamComponent(
                class_subject_id=subject.id,
                component_name=c["component_name"],
                max_marks=c["max_marks"],
                order_index=c["order_index"],
            ))
            inserted_components += 1
        inserted_subjects += 1

    db.commit()
    broker.publish("class_subjects", "bulk", id=0)
    log.info(
        "class subjects seeded from defaults",
        extra={"event": "class_subjects_seeded", "subjects": inserted_subjects, "components": inserted_components, "actor": user.name},
    )
    return {"subjects": inserted_subjects, "components": inserted_components}


# ── Exam-component endpoints ─────────────────────────────────────
@router.post("/{subject_id}/components", response_model=ExamComponentOut, status_code=201)
def add_component(
    subject_id: int,
    payload: ExamComponentCreate,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    subject = db.get(ClassSubject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    row = SubjectExamComponent(
        class_subject_id=subject_id,
        component_name=payload.component_name.strip(),
        max_marks=payload.max_marks,
        order_index=payload.order_index,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Component '{row.component_name}' already exists for this subject")
    db.refresh(row)
    broker.publish("class_subjects", "upsert", id=subject_id)
    log.info(
        "exam component added",
        extra={"event": "exam_component_added", "subject_id": subject_id, "component": row.component_name, "actor": user.name},
    )
    return row


@router.patch("/components/{component_id}", response_model=ExamComponentOut)
def update_component(
    component_id: int,
    payload: ExamComponentUpdate,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    row = db.get(SubjectExamComponent, component_id)
    if not row:
        raise HTTPException(status_code=404, detail="Component not found")
    data = payload.model_dump(exclude_unset=True)
    if "component_name" in data and data["component_name"]:
        row.component_name = data["component_name"].strip()
    if "max_marks" in data and data["max_marks"] is not None:
        row.max_marks = data["max_marks"]
    if "order_index" in data and data["order_index"] is not None:
        row.order_index = data["order_index"]
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Another component already has that name for this subject")
    db.refresh(row)
    broker.publish("class_subjects", "upsert", id=row.class_subject_id)
    return row


@router.delete("/components/{component_id}", status_code=204)
def delete_component(
    component_id: int,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    row = db.get(SubjectExamComponent, component_id)
    if not row:
        raise HTTPException(status_code=404, detail="Component not found")
    subject_id = row.class_subject_id
    db.delete(row)
    db.commit()
    broker.publish("class_subjects", "upsert", id=subject_id)


@router.put("/{subject_id}/components", response_model=ClassSubjectDetailOut)
def replace_components(
    subject_id: int,
    payload: ComponentsReplaceBody,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    """Replace the full component list for a subject in a single transaction.

    The detail page's spreadsheet-style editor uses this to commit all edits
    + deletes + adds with one Save click.
    """
    subject = db.execute(
        select(ClassSubject)
        .where(ClassSubject.id == subject_id)
        .options(selectinload(ClassSubject.components))
    ).scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Detect duplicates within the payload before touching the DB.
    names_lower = [c.component_name.strip().lower() for c in payload.components]
    if len(names_lower) != len(set(names_lower)):
        raise HTTPException(status_code=400, detail="Duplicate component names in the payload")

    for old in list(subject.components):
        db.delete(old)
    db.flush()

    for idx, c in enumerate(payload.components, start=1):
        db.add(SubjectExamComponent(
            class_subject_id=subject_id,
            component_name=c.component_name.strip(),
            max_marks=c.max_marks,
            order_index=c.order_index or idx,
        ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate component name (DB rejected)")
    db.refresh(subject)
    broker.publish("class_subjects", "upsert", id=subject_id)
    log.info(
        "exam components replaced",
        extra={"event": "exam_components_replaced", "subject_id": subject_id, "count": len(payload.components), "actor": user.name},
    )
    # Re-fetch with components eagerly loaded
    return db.execute(
        select(ClassSubject)
        .where(ClassSubject.id == subject_id)
        .options(selectinload(ClassSubject.components))
    ).scalar_one()
