"""Academic sessions (school years) and their term dates.

Anyone signed in can list them and read the current one (every class picker
and results screen needs that). Only super-admin creates or edits them.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..deps import CurrentUser, current_user, db_dep, require_super_admin
from ..logging_config import get_logger
from ..models.academic_session import AcademicSession
from ..schemas.academic_session import AcademicSessionCreate, AcademicSessionOut, AcademicSessionUpdate
from ..services.sessions import current_session, date_errors, default_dates, get_session, is_valid_session_name

router = APIRouter(prefix="/sessions", tags=["sessions"])
log = get_logger("app.audit.sessions")

_DATE_FIELDS = ("starts_on", "ends_on", "term1_start", "term1_end", "term2_start", "term2_end")


def _make_only_current(db: Session, keep_id: int) -> None:
    db.execute(update(AcademicSession).where(AcademicSession.id != keep_id).values(is_current=False))


@router.get("", response_model=list[AcademicSessionOut])
def list_sessions(user: CurrentUser = Depends(current_user), db: Session = Depends(db_dep)):
    return list(db.scalars(select(AcademicSession).order_by(AcademicSession.starts_on.desc())))


@router.get("/current", response_model=AcademicSessionOut)
def get_current(user: CurrentUser = Depends(current_user), db: Session = Depends(db_dep)):
    row = current_session(db)
    if not row:
        raise HTTPException(status_code=404, detail="No current academic session configured")
    return row


@router.post("", response_model=AcademicSessionOut, status_code=201)
def create_session(
    body: AcademicSessionCreate,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    name = body.session.strip()
    if not is_valid_session_name(name):
        raise HTTPException(status_code=422, detail="Session must look like 2026-27 (consecutive years)")
    if get_session(db, name):
        raise HTTPException(status_code=409, detail=f"Session {name} already exists")
    dates = default_dates(name)
    for f in _DATE_FIELDS:
        if getattr(body, f) is not None:
            dates[f] = getattr(body, f)
    errs = date_errors(dates)
    if errs:
        raise HTTPException(status_code=422, detail="; ".join(errs))
    row = AcademicSession(session=name, is_current=body.is_current, updated_by=user.name, **dates)
    db.add(row)
    db.flush()
    if body.is_current:
        _make_only_current(db, row.id)
    db.commit()
    db.refresh(row)
    log.info("academic_session_created", extra={"event": "academic_session_created", "session": name, "actor": user.name})
    return row


@router.patch("/{session_id}", response_model=AcademicSessionOut)
def update_session(
    session_id: int,
    body: AcademicSessionUpdate,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    row = db.get(AcademicSession, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    dates = {f: getattr(row, f) for f in _DATE_FIELDS}
    for f in _DATE_FIELDS:
        if getattr(body, f) is not None:
            dates[f] = getattr(body, f)
    errs = date_errors(dates)
    if errs:
        raise HTTPException(status_code=422, detail="; ".join(errs))
    for f, v in dates.items():
        setattr(row, f, v)
    if body.is_current is not None:
        row.is_current = body.is_current
        if body.is_current:
            _make_only_current(db, row.id)
    row.updated_by = user.name
    db.commit()
    db.refresh(row)
    log.info("academic_session_updated", extra={"event": "academic_session_updated", "session": row.session, "actor": user.name})
    return row
